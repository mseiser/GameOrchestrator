import unittest
import sqlite3
import tempfile
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database_manager import DBManager


class TestDatabaseFlow(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.temp_db.close()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS game_droplets (
                ipv4 TEXT PRIMARY KEY,
                connected_clients INTEGER NOT NULL DEFAULT 0,
                fresh_game INTEGER GENERATED ALWAYS AS (CASE WHEN connected_clients <= 0 THEN 1 ELSE 0 END) STORED,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                droplet_id INT NOT NULL DEFAULT 0,
                share_tag TEXT UNIQUE
            )
            """
        )
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS set_share_tag_after_insert
            AFTER INSERT ON game_droplets
            FOR EACH ROW
            WHEN NEW.share_tag IS NULL
            BEGIN
                UPDATE game_droplets
                SET share_tag = substr(hex(randomblob(3)), 1, 6)
                WHERE rowid = NEW.rowid;
            END;
            """
        )
        conn.commit()
        conn.close()

        self.db_manager = DBManager(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_reuse_then_remove_session_flow(self):
        self.db_manager.update_or_insert_game_droplet("10.0.9.1", 0)
        droplet_ip, share_tag = self.db_manager.get_droplets_without_player()

        self.assertEqual(droplet_ip, "10.0.9.1")
        self.assertIsNotNone(share_tag)

        self.assertTrue(self.db_manager.remove_droplet_from_db("10.0.9.1"))
        self.assertIsNone(self.db_manager.get_droplet_id("10.0.9.1"))


if __name__ == "__main__":
    unittest.main()
