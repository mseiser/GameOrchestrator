"""FastAPI endpoints"""

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlite3
import logging
import os
from dotenv import load_dotenv

load_dotenv()

try:
    # Try relative import first (for running as module/package)
    from .backend.droplet_manager import DropletManager
    from .backend.database_manager import DBManager
    from .backend.measurement_manager import MeasurementManager
    from .backend.domain_manager import SpaceshipDnsManager
    from .backend.security import require_internal_hmac
    from .backend.constants import (
        KEY_MESSAGE, KEY_SHARE_TAG, KEY_IP_ADDRESS, KEY_CONNECTED_CLIENTS, KEY_LAST_HEARTBEAT, KEY_DROPLET_ID,
        KEY_HOSTNAME, ERROR_DROPLET_NOT_FOUND_DB, MSG_HEARTBEAT_UPDATED
    )
except ImportError:
    # Fall back to absolute import (for Docker where workdir is /app)
    from backend.droplet_manager import DropletManager
    from backend.database_manager import DBManager
    from backend.measurement_manager import MeasurementManager
    from backend.domain_manager import SpaceshipDnsManager
    from backend.security import require_internal_hmac
    from backend.constants import (
        KEY_MESSAGE, KEY_SHARE_TAG, KEY_IP_ADDRESS, KEY_CONNECTED_CLIENTS, KEY_LAST_HEARTBEAT, KEY_DROPLET_ID,
        KEY_HOSTNAME, ERROR_DROPLET_NOT_FOUND_DB, MSG_HEARTBEAT_UPDATED
    )

databaseManager = DBManager()
dropletManager = DropletManager(databaseManager)
measurementManager = MeasurementManager()
domainManager = SpaceshipDnsManager()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed logs
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s') 
handler.setFormatter(formatter)
logger.addHandler(handler)
app = FastAPI(title="Game Orchestrator API")


def _get_cors_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


cors_allowed_origins = _get_cors_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "service": "orchestrator"}


@app.on_event("startup")
async def startup_event():
    logger.info("[API DEBUG] Game Orchestrator API starting up...")
    logger.info(f"[API DEBUG] CORS allowed origins: {cors_allowed_origins}")
    logger.info(f"[API DEBUG] HMAC key configured: {bool(os.getenv('INTERNAL_HMAC_KEY'))}")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"[REQUEST DEBUG] Incoming: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    response = await call_next(request)
    logger.info(f"[REQUEST DEBUG] Response: {request.method} {request.url.path} -> Status {response.status_code}")
    return response


class ServerHeartbeatRequest(BaseModel):
    share_tag: str
    connected_clients: int = Field(default=0, ge=0)


class ServerRegisterRequest(BaseModel):
    droplet_ip: str
    connected_clients: int = Field(default=0, ge=0)


class MeasurementEvent(BaseModel):
    """Mirrors PhysicsQuest.Measurements.MeasurementEvent (Unity).

    Serialised by Newtonsoft.Json as:
      { "type": "SubquestClosed", "timestamp": 1234567890.123,
        "payload": { "subquest": "...", "trials": 3, ... } }
    """
    type: str
    timestamp: float
    payload: dict = {}


class MeasurementEventBatch(BaseModel):
    client_id: str
    share_tag: str
    events: list[MeasurementEvent]


# WebGL Endpoints
@app.post("/sessions/start")
async def start_game_session_api():
    free_session = databaseManager.get_droplets_without_player()
    if free_session and free_session[0]:
        return {
            KEY_MESSAGE: "Reusing existing droplet",
            KEY_HOSTNAME: domainManager.get_hostname(free_session[1]),
            KEY_SHARE_TAG: free_session[1]
        }
    
    try:
        new_session = await dropletManager.create_droplet()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    new_share_tag = databaseManager.get_share_tag_by_ipv4(new_session)

    if not new_share_tag:
        raise HTTPException(status_code=500, detail="Droplet was created but share tag lookup failed.")

    return {
        KEY_HOSTNAME: domainManager.get_hostname(new_share_tag),
        KEY_SHARE_TAG: new_share_tag
    }

@app.post("/sessions/join")
def join_game_session_api(game_tag: str):
    game_tag = game_tag.lower()
    result = databaseManager.get_ipv4_by_share_tag(game_tag)
    if not result:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)
    return {
        KEY_HOSTNAME: domainManager.get_hostname(game_tag)}


@app.post("/measurements/report")
def report_measurements(batch: MeasurementEventBatch):
    """Accept a batch of gameplay measurement events from a WebGL client.

    The share_tag is validated against currently-known running sessions so
    random noise is filtered out, but the endpoint is otherwise unauthenticated
    (HMAC secrets must not be shipped in WebGL builds).
    """
    share_tag = batch.share_tag.lower()
    if not databaseManager.get_ipv4_by_share_tag(share_tag):
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)
    raw_events = [e.model_dump() for e in batch.events]
    inserted = measurementManager.insert_events(batch.client_id, share_tag, raw_events)
    logger.info(
        f"[MEASUREMENTS] client_id={batch.client_id!r} share_tag={share_tag!r} "
        f"events_received={len(batch.events)} events_inserted={inserted}"
    )
    return {KEY_MESSAGE: "Measurements recorded.", "inserted": inserted}


@app.get("/sessions/running")
def list_running_games_api():
    running_games = databaseManager.get_running_games()
    return [
        {
            KEY_HOSTNAME: domainManager.get_hostname(share_tag),
            KEY_CONNECTED_CLIENTS: connected_clients,
            KEY_LAST_HEARTBEAT: last_heartbeat,
            KEY_DROPLET_ID: droplet_id,
            KEY_SHARE_TAG: share_tag,
        }
        for ipv4, connected_clients, last_heartbeat, droplet_id, share_tag in running_games
    ]


# Server management endpoints (internal use only, protected by HMAC)
@app.post("/server/register")
def server_register(server_data: ServerRegisterRequest, _: None = Depends(require_internal_hmac)):
    if server_data.connected_clients < 0:
        raise HTTPException(status_code=422, detail="connected_clients cannot be negative.")

    try:
        existing_share_tag = domainManager.find_share_tag_by_ip(server_data.droplet_ip)
    except Exception as exc:
        logger.exception("DNS lookup failed for ip %s", server_data.droplet_ip)
        raise HTTPException(status_code=502, detail="DNS lookup failed.") from exc

    if existing_share_tag:
        # share_tag is UNIQUE, so only adopt the tag if it isn't already owned by a different live server.
        owner_ip = databaseManager.get_ipv4_by_share_tag(existing_share_tag)
        if owner_ip and owner_ip != server_data.droplet_ip:
            logger.warning(
                "DNS tag %s for ip %s is still owned by %s; issuing a fresh tag instead.",
                existing_share_tag, server_data.droplet_ip, owner_ip,
            )
            existing_share_tag = None

    if existing_share_tag:
        # IP already has a domain under a different tag; adopt it and keep that domain untouched.
        share_tag = databaseManager.register_server_with_share_tag(
            server_data.droplet_ip, server_data.connected_clients, existing_share_tag
        )
        if share_tag:
            hostname = domainManager.get_hostname(share_tag)
        else:
            existing_share_tag = None

    if not existing_share_tag:
        share_tag = databaseManager.register_server(
            server_data.droplet_ip,
            server_data.connected_clients,
        )
        if not share_tag:
            raise HTTPException(status_code=500, detail="Server registration did not produce a share tag.")

        try:
            hostname = domainManager.create_game_record(share_tag, server_data.droplet_ip)
        except Exception as exc:
            logger.exception("DNS registration failed for share tag %s", share_tag)
            raise HTTPException(status_code=502, detail="DNS registration failed.") from exc

    return {
        KEY_MESSAGE: "Server registered successfully.",
        KEY_IP_ADDRESS: server_data.droplet_ip,
        KEY_SHARE_TAG: share_tag,
        KEY_HOSTNAME: hostname,
    }


@app.post("/server/end")
def end_game_session_api(droplet_ip: str, _: None = Depends(require_internal_hmac)):
    logger.info(f"[API DEBUG] /server/end endpoint reached - droplet_ip: {droplet_ip}")
    droplet_id = databaseManager.get_droplet_id(droplet_ip)
    share_tag = databaseManager.get_share_tag_by_ipv4(droplet_ip)
    if not share_tag:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)

    try:
        domainManager.delete_game_record(share_tag)
        if droplet_id and droplet_id > 0:
            dropletManager.delete_droplet(droplet_id)
    except Exception as exc:
        logger.exception("Server cleanup failed for share tag %s", share_tag)
        raise HTTPException(status_code=502, detail="Server cleanup failed.") from exc

    databaseManager.remove_droplet_from_db(droplet_ip)
    if droplet_id and droplet_id > 0:
        return {KEY_MESSAGE: "Game session ended and DigitalOcean droplet deleted."}

    return {KEY_MESSAGE: "Game session ended and local session entry removed (no DigitalOcean droplet)."}


@app.post("/server/heartbeat")
def server_heartbeat(heartbeat_data: ServerHeartbeatRequest, _: None = Depends(require_internal_hmac)):
    share_tag = heartbeat_data.share_tag.lower()
    logger.info(f"[API DEBUG] /server/heartbeat endpoint reached - share_tag: {share_tag}, connected_clients: {heartbeat_data.connected_clients}")
    if heartbeat_data.connected_clients < 0:
        raise HTTPException(status_code=422, detail="connected_clients cannot be negative.")

    success = databaseManager.update_heartbeat_by_share_tag(
        share_tag,
        heartbeat_data.connected_clients,
    )

    if not success:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)
    return {
        KEY_MESSAGE: MSG_HEARTBEAT_UPDATED,
    }