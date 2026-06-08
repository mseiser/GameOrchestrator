"""DigitalOcean operations"""

import os
import logging
import asyncio
from dotenv import load_dotenv, find_dotenv
from pydo import Client
from .database_manager import DBManager

load_dotenv(find_dotenv())

from .constants import (
    WARN_DROPLET_NOT_IN_DB, ERROR_TOKEN_NOT_SET, ERROR_TAG_NOT_SET, ERROR_SNAPSHOT_NOT_SET
)

# Module logger for this manager
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed logs
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s') 
handler.setFormatter(formatter)
logger.addHandler(handler)

# Droplet creation defaults
_DEFAULT_SNAPSHOT_ID = os.getenv("SNAPSHOT_ID")
_DEFAULT_DROPLET_TAG = os.getenv("DROPLET_TAG")
_DIGITALOCEAN_TOKEN = os.getenv("DIGITALOCEAN_TOKEN")

class DropletManager:
    def __init__(self, dbManager: DBManager, token: str = None):
        self.dbManager = dbManager
        self.token = token or _DIGITALOCEAN_TOKEN
        self.droplet_tag = _DEFAULT_DROPLET_TAG
        self.snapshot_id = _DEFAULT_SNAPSHOT_ID
        self._require_token_and_tag()
        self.client = Client(token=self.token)

    def _require_token_and_tag(self):
        if not self.token:
            raise ValueError(ERROR_TOKEN_NOT_SET)
        if not self.droplet_tag:
            raise ValueError(ERROR_TAG_NOT_SET)
        if not self.snapshot_id:
            raise ValueError(ERROR_SNAPSHOT_NOT_SET)
        logger.debug("Droplet tag: %s", self.droplet_tag)
        logger.debug("Snapshot ID: %s", self.snapshot_id)
        logger.debug("Token preview: %s", repr(_DIGITALOCEAN_TOKEN[:8] + "..." + _DIGITALOCEAN_TOKEN[-8:]))

    @staticmethod
    def _extract_droplet_list(response):
        if isinstance(response, dict):
            droplets = response.get("droplets")
            if droplets is not None:
                return droplets
        if isinstance(response, list):
            return response
        return []

    @staticmethod
    def _extract_droplet(response):
        if isinstance(response, dict):
            if "droplet" in response and isinstance(response["droplet"], dict):
                return response["droplet"]
            return response
        return response

    @staticmethod
    def _extract_ipv4(droplet):
        try:
            return droplet["networks"]["v4"][0]["ip_address"]
        except (KeyError, IndexError, TypeError):
            return None
    
    def _fetch_tagged_droplets(self):
        response = self.client.droplets.list(tag_name=self.droplet_tag)
        droplets = self._extract_droplet_list(response)
        self.dbManager.update_db_with_droplets(droplets)
        return droplets

    def get_droplet_id(self, droplet_ip: str):
        result = self.dbManager.get_droplet_id(droplet_ip)
        if result:
            return result

        fetch_result = self._fetch_tagged_droplets()
        for droplet in fetch_result:
            ipv4 = self._extract_ipv4(droplet)
            if ipv4 == droplet_ip:
                return droplet.get("id")

        logger.warning(WARN_DROPLET_NOT_IN_DB.format(droplet_id=droplet_ip))
        return None
    
    def delete_droplet(self, droplet_id: int):
        self.client.droplets.destroy(droplet_id)
        return {"message": f"Droplet {droplet_id} deleted successfully."}
    
    async def create_droplet(self):
        create_request = {
            "name": f"g-{self.droplet_tag}",
            "size": "s-1vcpu-1gb",
            "image": _DEFAULT_SNAPSHOT_ID,
            "tags": [self.droplet_tag]
        }
        response = self.client.droplets.create(body=create_request)
        new_droplet_id = response["droplet"]["id"] 
        
        if not new_droplet_id:
            raise ValueError("Droplet creation response missing droplet id. Something went wrong with the DigitalOcean API request.")

        # Wait for droplet to be active and get details
        new_droplet_ip = None
        for _ in range(30):  # Retry for up to ~5 minutes
            await asyncio.sleep(10) # Wait before checking status
            new_droplet_details = self.client.droplets.get(new_droplet_id)
            new_ip_address = self._extract_ipv4(new_droplet_details)
            if new_ip_address:
                break
        if not new_droplet_ip:
            raise ValueError("Droplet creation response missing id or ipv4 address.")
        
        self.dbManager.insert_new_droplet(new_droplet_id, new_ip_address)
        return new_droplet_ip
              
       
