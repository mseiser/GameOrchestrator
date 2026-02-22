import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database_manager import DBManager


class TestDBManager(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self._create_schema(self.db_path)
        self.db_manager = DBManager(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _create_schema(self, db_path):
        conn = sqlite3.connect(db_path)
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

    def _seed_multiple_entries(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO game_droplets (ipv4, connected_clients, droplet_id, share_tag) VALUES (?, ?, ?, ?)",
            ("10.0.0.1", 0, 101, "TAG101"),
        )
        cur.execute(
            "INSERT INTO game_droplets (ipv4, connected_clients, droplet_id, share_tag) VALUES (?, ?, ?, ?)",
            ("10.0.0.2", 2, 102, "TAG102"),
        )
        cur.execute(
            "INSERT INTO game_droplets (ipv4, connected_clients, droplet_id, share_tag) VALUES (?, ?, ?, ?)",
            ("10.0.0.3", 0, 103, "TAG103"),
        )
        conn.commit()
        conn.close()

    def test_get_droplets_without_player_empty_db(self):
        self.assertEqual(self.db_manager.get_droplets_without_player(), (None, None))

    def test_get_droplets_without_player_with_multiple_entries(self):
        self._seed_multiple_entries()

        ipv4, share_tag = self.db_manager.get_droplets_without_player()

        self.assertIn((ipv4, share_tag), [("10.0.0.1", "TAG101"), ("10.0.0.3", "TAG103")])

    def test_update_or_insert_game_droplet_insert_and_update(self):
        inserted = self.db_manager.update_or_insert_game_droplet("10.0.1.1", 0)
        updated = self.db_manager.update_or_insert_game_droplet("10.0.1.1", 4)

        self.assertTrue(inserted)
        self.assertTrue(updated)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT connected_clients FROM game_droplets WHERE ipv4 = ?", ("10.0.1.1",))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row[0], 4)

    def test_update_db_with_droplets_on_empty_db(self):
        droplets = [
            {"id": 201, "networks": {"v4": [{"ip_address": "10.0.2.1"}]}},
            {"id": 202, "networks": {"v4": [{"ip_address": "10.0.2.2"}]}},
        ]

        self.db_manager.update_db_with_droplets(droplets)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT ipv4, droplet_id FROM game_droplets ORDER BY ipv4")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(rows, [("10.0.2.1", 201), ("10.0.2.2", 202)])

    def test_update_db_with_droplets_updates_existing_entry(self):
        self._seed_multiple_entries()

        self.db_manager.update_db_with_droplets(
            [{"id": 999, "networks": {"v4": [{"ip_address": "10.0.0.2"}]}}]
        )

        self.assertEqual(self.db_manager.get_droplet_id("10.0.0.2"), 999)

    def test_getters_for_existing_and_missing_entries(self):
        self._seed_multiple_entries()

        self.assertEqual(self.db_manager.get_droplet_id("10.0.0.1"), 101)
        self.assertEqual(self.db_manager.get_droplet_id("10.9.9.9"), None)

        self.assertEqual(self.db_manager.get_ipv4_by_share_tag("TAG102"), "10.0.0.2")
        self.assertEqual(self.db_manager.get_ipv4_by_share_tag("MISSING"), None)

        self.assertEqual(self.db_manager.get_share_tag_by_ipv4("10.0.0.3"), "TAG103")
        self.assertEqual(self.db_manager.get_share_tag_by_ipv4("10.9.9.9"), None)

    def test_add_and_remove_droplet(self):
        self.db_manager._add_droplet_to_db("10.0.5.1")
        self.assertEqual(self.db_manager.get_droplet_id("10.0.5.1"), 0)

        removed = self.db_manager.remove_droplet_from_db("10.0.5.1")
        self.assertTrue(removed)
        self.assertIsNone(self.db_manager.get_droplet_id("10.0.5.1"))

    def test_schema_creation(self):
        """Test that the database schema can be created without SQL syntax errors."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = temp_db.name
        temp_db.close()

        try:
            # Should not raise any SQL syntax errors
            self._create_schema(db_path)
            
            # Verify table was created
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_droplets'")
            result = cur.fetchone()
            conn.close()
            
            self.assertIsNotNone(result, "game_droplets table should exist")
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == "__main__":
    unittest.main()
