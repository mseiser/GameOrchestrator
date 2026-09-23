import os
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class SpaceshipDnsManager:

    def __init__(self):
        self.api_key = os.environ["SPACESHIP_API_KEY"]
        self.api_secret = os.environ["SPACESHIP_API_SECRET"]
        self.zone = os.getenv("SPACESHIP_DNS_ZONE", "physicsquest.xyz")

        self.headers = {
            "X-Api-Key": self.api_key,
            "X-Api-Secret": self.api_secret,
            "Content-Type": "application/json",
        }

    def get_hostname(self, share_tag: str) -> str:
        return f"{share_tag.lower()}.servers.{self.zone}"

    def create_game_record(self, share_tag: str, ip_address: str):
        share_tag = share_tag.lower()
        record_name = f"{share_tag}.servers"
        url = f"https://spaceship.dev/api/v1/dns/records/{self.zone}"

        payload = {
            "force": True,
            "items": [
                {
                    "type": "A",
                    "address": ip_address,
                    "name": record_name,
                    "ttl": 3600
                }
            ]
        }

        response = requests.put(url, json=payload, headers=self.headers, timeout=10)
        response.raise_for_status()

        print(f"[DNS DEBUG] Creating DNS record for droplet {share_tag} with IP {ip_address}: {response.status_code} - {response.text}")

        return record_name

    def find_share_tag_by_ip(self, ip_address: str, exclude_share_tag: str | None = None):
        """Return the share tag of an existing '.servers' A record pointing at ip_address, if any."""
        url = f"https://spaceship.dev/api/v1/dns/records/{self.zone}"
        exclude_share_tag = exclude_share_tag.lower() if exclude_share_tag else None

        skip = 0
        take = 500
        while True:
            response = requests.get(
                url, headers=self.headers, params={"take": take, "skip": skip}, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])

            for record in items:
                if record.get("type") != "A" or record.get("address") != ip_address:
                    continue
                name = record.get("name", "").lower()
                if not name.endswith(".servers"):
                    continue
                share_tag = name[: -len(".servers")]
                if share_tag and share_tag != exclude_share_tag:
                    return share_tag

            skip += take
            if skip >= data.get("total", 0):
                return None

    def ensure_record_exists(self, share_tag: str, ip_address: str):
        share_tag = share_tag.lower()
        record_name = f"{share_tag}.servers"
        url = f"https://spaceship.dev/api/v1/dns/records/{self.zone}/{record_name}"

        response = requests.get(url, headers=self.headers, timeout=10)

        if response.status_code == 404:
            print(f"[DNS DEBUG] DNS record for {record_name} not found. Creating new record.")
            return self.create_game_record(share_tag, ip_address)
        elif response.status_code == 200:
            print(f"[DNS DEBUG] DNS record for {record_name} already exists.")
            return record_name
        else:
            print(f"[DNS DEBUG] Error checking DNS record for {record_name}: {response.status_code} - {response.text}")
            return None

    def delete_game_record(self, share_tag: str):
        share_tag = share_tag.lower()
        record_name = f"{share_tag}.servers"
        url = f"https://spaceship.dev/api/v1/dns/records/{self.zone}/{record_name}"

        response = requests.delete(url, headers=self.headers, timeout=10)

        if response.status_code in (200, 204, 404):
            print(f"[DNS DEBUG] Successfully deleted DNS record for {record_name}.")
            return True
        else:
            print(f"[DNS DEBUG] Error deleting DNS record for {record_name}: {response.status_code} - {response.text}")
            return False