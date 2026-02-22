import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.droplet_manager import DropletManager


class TestDropletManager(unittest.TestCase):
    def setUp(self):
        self.db_manager = MagicMock()
        self.manager = DropletManager(self.db_manager, token="test-token")

    @patch("backend.droplet_manager.requests.get")
    def test_fetch_tagged_droplets_updates_database(self, mock_get):
        droplets = [{"id": 1, "networks": {"v4": [{"ip_address": "10.0.0.1"}]}}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"droplets": droplets}
        mock_get.return_value = mock_response

        result = self.manager._fetch_tagged_droplets()

        self.assertEqual(result, droplets)
        self.db_manager.update_db_with_droplets.assert_called_once_with(droplets)

    def test_get_droplet_id_returns_from_db(self):
        self.db_manager.get_droplet_id.return_value = 55

        result = self.manager.get_droplet_id("10.0.0.55")

        self.assertEqual(result, 55)
        self.db_manager.get_droplet_id.assert_called_once_with("10.0.0.55")

    def test_get_droplet_id_fetches_when_missing(self):
        self.db_manager.get_droplet_id.return_value = None
        with patch.object(
            self.manager,
            "_fetch_tagged_droplets",
            return_value=[{"id": 88, "networks": {"v4": [{"ip_address": "10.0.0.88"}]}}],
        ) as mock_fetch:
            result = self.manager.get_droplet_id("10.0.0.88")

        self.assertEqual(result, 88)
        mock_fetch.assert_called_once()

    @patch("backend.droplet_manager.requests.delete")
    def test_delete_droplet_success(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        result = self.manager.delete_droplet(99)

        self.assertEqual(result, {"message": "Droplet 99 deleted successfully."})

    @patch("backend.droplet_manager.requests.post")
    def test_create_droplet_updates_database(self, mock_post):
        new_droplet = {
            "id": 777,
            "networks": {"v4": [{"ip_address": "10.0.7.7"}]}
        }
        mock_create_response = MagicMock()
        mock_create_response.status_code = 202
        mock_create_response.json.return_value = {"droplet": new_droplet}

        mock_ip_response = MagicMock()
        mock_ip_response.status_code = 200
        mock_ip_response.json.return_value = {"ip_address": "10.0.7.7"}

        mock_post.side_effect = [mock_create_response, mock_ip_response]

        async def run_create():
            return await self.manager.create_droplet()

        import asyncio
        result = asyncio.run(run_create())

        self.assertEqual(result, "10.0.7.7")
        self.db_manager.update_db_with_droplets.assert_called_once_with([new_droplet])


if __name__ == "__main__":
    unittest.main()
