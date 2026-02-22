import sys
import os
import unittest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
import api


class TestApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_start_game_session_reuses_existing_droplet(self):
        with patch.object(api.databaseManager, "get_droplets_without_player", return_value=("10.0.0.1", "ABC123")):
            response = self.client.post("/sessions/start")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "message": "Reusing existing droplet",
                "ip_address": "10.0.0.1",
                "share_tag": "ABC123",
            },
        )

    def test_start_game_session_creates_new_droplet(self):
        with (
            patch.object(api.databaseManager, "get_droplets_without_player", return_value=(None, None)),
            patch.object(api.dropletManager, "create_droplet", new=AsyncMock(return_value="10.0.0.9")),
            patch.object(api.databaseManager, "get_share_tag_by_ipv4", return_value="NEWTAG"),
        ):
            response = self.client.post("/sessions/start")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ip_address": "10.0.0.9",
                "share_tag": "NEWTAG",
            },
        )

    def test_login_game_session_success(self):
        with patch.object(api.databaseManager, "get_ipv4_by_share_tag", return_value="10.0.0.2"):
            response = self.client.post("/sessions/join", params={"game_tag": "ABC123"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ip_address": "10.0.0.2"})

    def test_login_game_session_failure(self):
        with patch.object(api.databaseManager, "get_ipv4_by_share_tag", return_value=None):
            response = self.client.post("/sessions/join", params={"game_tag": "MISSING"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Droplet not found in database."})

    def test_end_game_session_success(self):
        with (
            patch.object(api.databaseManager, "get_droplet_id", return_value=77),
            patch.object(api.dropletManager, "delete_droplet", return_value={"message": "ok"}),
            patch.object(api.databaseManager, "remove_droplet_from_db", return_value=True),
        ):
            response = self.client.post("/sessions/end", params={"droplet_ip": "10.0.0.3"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Game session ended and DigitalOcean droplet deleted."})

    def test_end_game_session_failure(self):
        with (
            patch.object(api.databaseManager, "get_droplet_id", return_value=None),
            patch.object(api.databaseManager, "remove_droplet_from_db", return_value=False),
        ):
            response = self.client.post("/sessions/end", params={"droplet_ip": "10.0.0.33"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Droplet not found in database."})

    def test_end_game_session_local_session_without_do_droplet(self):
        with (
            patch.object(api.databaseManager, "get_droplet_id", return_value=0),
            patch.object(api.databaseManager, "remove_droplet_from_db", return_value=True),
            patch.object(api.dropletManager, "delete_droplet") as mock_delete,
        ):
            response = self.client.post("/sessions/end", params={"droplet_ip": "127.0.0.1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"message": "Game session ended and local session entry removed (no DigitalOcean droplet)."},
        )
        mock_delete.assert_not_called()

    def test_server_heartbeat_success(self):
        with patch.object(api.databaseManager, "update_or_insert_game_droplet", return_value=True):
            response = self.client.post(
                "/server/heartbeat",
                json={"droplet_ip": "10.0.0.4", "connected_clients": 10},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "message": "Heartbeat updated successfully.",
                "ip_address": "10.0.0.4",
                "connected_clients": 10,
            },
        )

    def test_server_heartbeat_failure(self):
        with patch.object(api.databaseManager, "update_or_insert_game_droplet", return_value=False):
            response = self.client.post(
                "/server/heartbeat",
                json={"droplet_ip": "10.0.0.5", "connected_clients": 10},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Droplet not found in database."})


if __name__ == "__main__":
    unittest.main()
