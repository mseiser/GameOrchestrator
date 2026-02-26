import hashlib
import hmac
import json
import os
import sys
import time
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.security import require_internal_hmac


def _sign_headers(secret: str, method: str, path: str, query: str = "", body: bytes = b"", timestamp: int | None = None):
    current_timestamp = int(time.time()) if timestamp is None else int(timestamp)
    timestamp_str = str(current_timestamp)
    body_hash = hashlib.sha256(body).hexdigest()
    message = "\n".join([method.upper(), path, query, timestamp_str, body_hash])
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "Request-Timestamp": timestamp_str,
        "Request-Signature": signature,
    }


class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.secret = "test-hmac-secret"
        self.app = FastAPI()

        @self.app.post("/protected")
        def protected(_: None = Depends(require_internal_hmac)):
            return {"ok": True}

        self.client = TestClient(self.app)

    def test_valid_hmac_with_query(self):
        query = "foo=bar"
        headers = _sign_headers(self.secret, "POST", "/protected", query=query)

        with patch.dict(os.environ, {"INTERNAL_HMAC_KEY": self.secret}, clear=False):
            response = self.client.post("/protected", params={"foo": "bar"}, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_valid_hmac_with_json_body(self):
        payload = {"droplet_ip": "10.0.0.1", "connected_clients": 2}
        body = json.dumps(payload).encode("utf-8")
        headers = _sign_headers(self.secret, "POST", "/protected", body=body)
        headers["Content-Type"] = "application/json"

        with patch.dict(os.environ, {"INTERNAL_HMAC_KEY": self.secret}, clear=False):
            response = self.client.post("/protected", content=body, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_valid_hmac_with_hyphenated_headers(self):
        # This test now verifies that headers are already hyphenated
        headers = _sign_headers(self.secret, "POST", "/protected")

        with patch.dict(os.environ, {"INTERNAL_HMAC_KEY": self.secret}, clear=False):
            response = self.client.post("/protected", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_missing_secret_returns_503(self):
        headers = _sign_headers(self.secret, "POST", "/protected")

        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post("/protected", headers=headers)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Internal endpoint unavailable."})

    def test_missing_headers_returns_401(self):
        with patch.dict(os.environ, {"INTERNAL_HMAC_KEY": self.secret}, clear=False):
            response = self.client.post("/protected")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid HMAC signature."})

    def test_stale_signature_returns_401(self):
        stale_timestamp = int(time.time()) - 1000
        headers = _sign_headers(self.secret, "POST", "/protected", timestamp=stale_timestamp)

        with patch.dict(os.environ, {"INTERNAL_HMAC_KEY": self.secret}, clear=False):
            response = self.client.post("/protected", headers=headers)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Stale HMAC signature."})


if __name__ == "__main__":
    unittest.main()
