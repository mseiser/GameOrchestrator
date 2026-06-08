"""Small client for the running-games endpoint."""

import json
import os
import sys

import requests


def main() -> int:
    base_url = os.getenv("ORCHESTRATOR_BASE_URL", "https://femquestorchestrator.mariasgames.xyz").rstrip("/")
    url = f"{base_url}/sessions/running"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    try:
        payload = response.json()
    except ValueError:
        print("Server returned non-JSON response:", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())