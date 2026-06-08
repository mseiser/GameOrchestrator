import os
from azure.core.credentials import AccessToken
from pydo import Client
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import time

env_path = Path(__file__).resolve().parent / ".env"
print("Exists:", env_path.exists())

load_dotenv(find_dotenv())
_API_TOKEN = os.getenv("DIGITALOCEAN_TOKEN")
_DROPLET_TAG = os.getenv("DROPLET_TAG")
_SNAPSHOT_ID = os.getenv("SNAPSHOT_ID")

if not _API_TOKEN:
    raise ValueError("DIGITALOCEAN_TOKEN is not set in environment variables.")

print("Token preview:", repr(_API_TOKEN[:8] + "..." + _API_TOKEN[-8:]))

client = Client(token=_API_TOKEN)

# get snapshot 
if not _SNAPSHOT_ID:
    raise ValueError("SNAPSHOT_ID is not set in environment variables.")

snapshot = client.snapshots.get(_SNAPSHOT_ID)
print("Snapshot details:", snapshot)

# list droplets with tag
if not _DROPLET_TAG:
    raise ValueError("DROPLET_TAG is not set in environment variables.")

droplets_with_tag = client.droplets.list(tag_name=_DROPLET_TAG)
for droplet in droplets_with_tag["droplets"]:
    print(droplet["name"], droplet["id"], droplet["status"], droplet["networks"]["v4"][0]["ip_address"])

# create droplet from snapshot
# droplet_name = "test-droplet-from-snapshot"
# req = {
#     "name": droplet_name,
#     "region": "fra1",
#     "size": "s-1vcpu-1gb",
#     "image": _SNAPSHOT_ID,
#     "tags": [_DROPLET_TAG]
# }
# new_droplet = client.droplets.create(body=req)
# print("Created droplet:", new_droplet)
# time.sleep(120)  # Wait for droplet to be created and active

# Get Ip address of the new droplet
#droplet_id = new_droplet["droplet"]["id"]
new_droplet_details = client.droplets.get(573154347)
print("New droplet details:", new_droplet_details)
ip_address = new_droplet_details["droplet"]["networks"]["v4"][0]["ip_address"]
print("New droplet IP address:", ip_address)
