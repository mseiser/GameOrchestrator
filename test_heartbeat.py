import requests
import hashlib
import hmac
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:8000"
DROPLET_IP = "172.19.32.1"
CONNECTED_CLIENTS = 0

# Get HMAC key
hmac_key = os.getenv("INTERNAL_HMAC_KEY")
if not hmac_key:
    print("ERROR: INTERNAL_HMAC_KEY not found")
    exit(1)

# Build request
method = "POST"
path = "/server/heartbeat"
query = ""
timestamp = str(int(datetime.utcnow().timestamp()))

# Build body
payload = {
    "droplet_ip": DROPLET_IP,
    "connected_clients": CONNECTED_CLIENTS
}
body = json.dumps(payload, separators=(',', ':'))
body_bytes = body.encode('utf-8')

# Calculate body hash
body_hash = hashlib.sha256(body_bytes).hexdigest()

# Build message for HMAC
message = f"{method}\n{path}\n{query}\n{timestamp}\n{body_hash}"
print(f"Message to sign:\n{repr(message)}\n")

# Calculate signature
signature = hmac.new(
    hmac_key.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"Timestamp: {timestamp}")
print(f"Body: {body}")
print(f"Body hash: {body_hash}")
print(f"Signature: {signature}\n")

# Make request
url = f"{BASE_URL}{path}"
headers = {
    "Request-Timestamp": timestamp,
    "Request-Signature": signature,
    "Content-Type": "application/json"
}

print(f"Making request to: {url}")
print(f"Headers: {headers}\n")

try:
    response = requests.post(url, headers=headers, data=body, timeout=5)
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response body: {response.text}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
