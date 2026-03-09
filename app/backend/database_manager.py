"""Database operations"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

_ENV_DB_PATH = os.getenv("DB_PATH")

class DBManager:
    def __init__(self, db=None):
        self.db = db or _ENV_DB_PATH

    def update_db_with_droplets(self, droplets):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        for droplet in droplets:
            ipv4 = droplet["networks"]["v4"][0]["ip_address"]
            droplet_id = droplet["id"]
            cur.execute(
                """
                INSERT INTO game_droplets (ipv4, droplet_id)
                VALUES (?, ?)
                ON CONFLICT(ipv4) DO UPDATE SET
                    droplet_id=excluded.droplet_id,
                    last_heartbeat=CURRENT_TIMESTAMP
                """,
                (ipv4, droplet_id),
            )
        conn.commit()
        conn.close()

    def update_or_insert_game_droplet(self, droplet_ip: str, connected_clients: int):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO game_droplets (ipv4, connected_clients, last_heartbeat)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ipv4) DO UPDATE SET
                connected_clients=excluded.connected_clients,
                last_heartbeat=CURRENT_TIMESTAMP
            """,
            (droplet_ip, connected_clients),
        )
        conn.commit()
        conn.close()
        return True

    def get_droplets_without_player(self):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ipv4, share_tag FROM game_droplets
            WHERE fresh_game = 1
            ORDER BY last_heartbeat ASC
            """,
        )
        droplets = [row for row in cur.fetchall()]
        conn.close()

        ipv4, share_tag = droplets[0] if droplets else (None, None)
        return ipv4, share_tag

    def _add_droplet_to_db(self, ipv4: str):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO game_droplets (ipv4)
            VALUES (?)
            """,
            (ipv4,),
        )
        conn.commit()
        conn.close()

    def remove_droplet_from_db(self, ipv4: str):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM game_droplets
            WHERE ipv4 = ?
            """,
            (ipv4,),
        )
        removed_rows = cur.rowcount
        conn.commit()
        conn.close()
        return removed_rows > 0

    def get_droplet_id(self, ipv4: str):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT droplet_id FROM game_droplets
            WHERE ipv4 = ?
            """,
            (ipv4,),
        )
        result = cur.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_ipv4_by_share_tag(self, share_tag: str):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ipv4 FROM game_droplets
            WHERE share_tag = ?
            """,
            (share_tag,),
        )
        result = cur.fetchone()
        conn.close()
        return result[0] if result else None

    def get_share_tag_by_ipv4(self, ipv4: str):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT share_tag FROM game_droplets
            WHERE ipv4 = ?
            """,
            (ipv4,),
        )
        result = cur.fetchone()
        conn.close()
        return result[0] if result else None