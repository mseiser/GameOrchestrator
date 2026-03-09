"""DigitalOcean operations"""

import os
import requests
from .constants import (
    WARN_DROPLET_NOT_IN_DB, ERROR_TOKEN_NOT_SET, ERROR_TAG_NOT_SET
)

# Droplet creation defaults
_DEFAULT_SNAPSHOT_ID = os.getenv("SNAPSHOT_ID", None)
_DEFAULT_DROPLET_TAG = os.getenv("DROPLET_TAG", "femquest-server")
_DEFAULT_REGION = os.getenv("DROPLET_REGION", "nyc3")
_DEFAULT_SIZE = os.getenv("DROPLET_SIZE", "s-1vcpu-1gb")

# API URLs
_DIGITALOCEAN_API_BASE = "https://api.digitalocean.com/v2"
_DIGITALOCEAN_DROPLETS_URL = f"{_DIGITALOCEAN_API_BASE}/droplets"
_DIGITALOCEAN_TOKEN = os.getenv("DIGITALOCEAN_TOKEN", None)

from .database_manager import DBManager

class DropletManager:
    def __init__(self, dbManager: DBManager, token: str = None):
        self.dbManager = dbManager
        self.token = token or _DIGITALOCEAN_TOKEN
        self.droplet_tag = _DEFAULT_DROPLET_TAG
        self._require_token_and_tag()
        self.headers = self._headers()

    def _require_token_and_tag(self):
        if not self.token:
            raise ValueError(ERROR_TOKEN_NOT_SET)
        if not self.droplet_tag:
            raise ValueError(ERROR_TAG_NOT_SET)
        
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _fetch_tagged_droplets(self):
        params = {"tag_name": self.droplet_tag}
        response = requests.get(_DIGITALOCEAN_DROPLETS_URL, headers=self.headers, params=params, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch droplets: {response.text}")
        
        self.dbManager.update_db_with_droplets(response.json().get("droplets", []))
        return response.json().get("droplets", [])

    def get_droplet_id(self, droplet_ip: str):
        result = self.dbManager.get_droplet_id(droplet_ip)
        if result:
            return result
        else:
            _fetch_result = self._fetch_tagged_droplets()
            for droplet in _fetch_result:
                ipv4 = droplet["networks"]["v4"][0]["ip_address"]
                if ipv4 == droplet_ip:
                    return droplet["id"]
            print(WARN_DROPLET_NOT_IN_DB.format(droplet_id=droplet_ip))
        return None
    
    def delete_droplet(self, droplet_id: int):
        response = requests.delete(f"{_DIGITALOCEAN_DROPLETS_URL}/{droplet_id}", headers=self.headers, timeout=10)
        if response.status_code != 204:
            raise Exception(f"Failed to delete droplet {droplet_id}: {response.text}")
        return {"message": f"Droplet {droplet_id} deleted successfully."}
    
    async def create_droplet(self):
        data = {
            "name": f"game-session-{self.droplet_tag}",
            "region": _DEFAULT_REGION,
            "size": _DEFAULT_SIZE,
            "image": _DEFAULT_SNAPSHOT_ID,
            "tags": [self.droplet_tag]
        }
        response = requests.post(_DIGITALOCEAN_DROPLETS_URL, headers=self.headers, json=data, timeout=10)
        if response.status_code != 202:
            raise Exception(f"Failed to create droplet: {response.text}")
        
        new_droplet = response.json().get("droplet", {})
        # print(f"Created droplet response: {response.json()}")
        if not new_droplet:
            raise Exception("Droplet creation response did not contain droplet data.")
        id = new_droplet.get("id")
        
        response_ip = requests.post(f"{_DIGITALOCEAN_DROPLETS_URL}/{id}", headers=self.headers, timeout=10)
        if response_ip.status_code != 200:
            raise Exception(f"Failed to get IP for droplet {id}: {response_ip.text}")
        ipv4 = response_ip.json().get("ip_address")
        if not id or not ipv4:
            raise Exception("Droplet creation response missing id or ipv4 address.")
        
        self.dbManager.update_db_with_droplets([new_droplet])
        return ipv4
              
       
