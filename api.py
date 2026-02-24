"""FastAPI endpoints"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os
from dotenv import load_dotenv

from backend.droplet_manager import DropletManager
from backend.database_manager import DBManager
from backend.constants import (
    KEY_ERROR, KEY_MESSAGE, KEY_SHARE_TAG, KEY_IP_ADDRESS, KEY_CONNECTED_CLIENTS,
    ERROR_DROPLET_NOT_FOUND_DB, MSG_HEARTBEAT_UPDATED, KEY_LAST_HEARTBEAT
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
    
    new_session = await dropletManager.create_droplet()
    new_share_tag = databaseManager.get_share_tag_by_ipv4(new_session)

    if KEY_ERROR in new_session or not new_share_tag:
        raise HTTPException(status_code=500, detail=new_session[KEY_ERROR])

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


@app.post("/sessions/end")
def end_game_session_api(droplet_ip: str):
    droplet_id = databaseManager.get_droplet_id(droplet_ip)
    removed = databaseManager.remove_droplet_from_db(droplet_ip)
    if not removed:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)

    if droplet_id and droplet_id > 0:
        dropletManager.delete_droplet(droplet_id)
        return {KEY_MESSAGE: "Game session ended and DigitalOcean droplet deleted."}

    return {KEY_MESSAGE: "Game session ended and local session entry removed (no DigitalOcean droplet)."}


@app.post("/server/heartbeat")
def server_heartbeat(request: ServerHeartbeatRequest):
    success = databaseManager.update_or_insert_game_droplet(request.droplet_ip, request.connected_clients)
    if not success:
        raise HTTPException(status_code=404, detail=ERROR_DROPLET_NOT_FOUND_DB)
    return {
        KEY_MESSAGE: MSG_HEARTBEAT_UPDATED,
        KEY_IP_ADDRESS: request.droplet_ip,
        KEY_CONNECTED_CLIENTS: request.connected_clients
    }
