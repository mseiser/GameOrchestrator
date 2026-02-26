"""FastAPI endpoints"""

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os
from dotenv import load_dotenv

from backend.droplet_manager import DropletManager
from backend.database_manager import DBManager
from backend.security import require_internal_hmac
from backend.constants import (
    KEY_ERROR, KEY_MESSAGE, KEY_SHARE_TAG, KEY_IP_ADDRESS, KEY_CONNECTED_CLIENTS,
    ERROR_DROPLET_NOT_FOUND_DB, MSG_HEARTBEAT_UPDATED
)

databaseManager = DBManager()
dropletManager = DropletManager(databaseManager)

load_dotenv()

logger = logging.getLogger(__name__)
app = FastAPI(title="Game Orchestrator API")


def _get_cors_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if raw_origins.strip():
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    return [
        "https://test.femquest.gamelabgraz",
        "https://test.femquest.gamelabgraz.at",
        "https://femquest.gamelabgraz.at",
    ]


cors_allowed_origins = _get_cors_allowed_origins()
_CORS_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_origin_regex=_CORS_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    droplet_ip: str
    connected_clients: int


# API Endpoints
@app.post("/sessions/start")
async def start_game_session_api():
    free_session = databaseManager.get_droplets_without_player()
    if free_session and free_session[0]:
        return {
            KEY_MESSAGE: "Reusing existing droplet",
            KEY_IP_ADDRESS: free_session[0],
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
        KEY_IP_ADDRESS: new_session,
        KEY_SHARE_TAG: new_share_tag
    }

@app.post("/sessions/join")
def join_game_session_api(game_tag: str):
    result = databaseManager.get_ipv4_by_share_tag(game_tag)
    if not result:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)
    return {
        KEY_IP_ADDRESS: result}


@app.post("/server/end")
def end_game_session_api(droplet_ip: str, _: None = Depends(require_internal_hmac)):
    logger.info(f"[API DEBUG] /server/end endpoint reached - droplet_ip: {droplet_ip}")
    droplet_id = databaseManager.get_droplet_id(droplet_ip)
    removed = databaseManager.remove_droplet_from_db(droplet_ip)
    if not removed:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)

    if droplet_id and droplet_id > 0:
        dropletManager.delete_droplet(droplet_id)
        return {KEY_MESSAGE: "Game session ended and DigitalOcean droplet deleted."}

    return {KEY_MESSAGE: "Game session ended and local session entry removed (no DigitalOcean droplet)."}


@app.post("/server/heartbeat")
def server_heartbeat(heartbeat_data: ServerHeartbeatRequest, _: None = Depends(require_internal_hmac)):
    logger.info(f"[API DEBUG] /server/heartbeat endpoint reached - droplet_ip: {heartbeat_data.droplet_ip}, connected_clients: {heartbeat_data.connected_clients}")
    success = databaseManager.update_or_insert_game_droplet(heartbeat_data.droplet_ip, heartbeat_data.connected_clients)
    if not success:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)
    return {
        KEY_MESSAGE: MSG_HEARTBEAT_UPDATED,
    }
