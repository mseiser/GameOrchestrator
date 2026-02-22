"""SQL-Schema Initialization"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS game_droplets (
    ipv4 TEXT PRIMARY KEY,
    connected_clients INTEGER NOT NULL DEFAULT 0,
    fresh_game INTEGER GENERATED ALWAYS AS (CASE WHEN connected_clients <= 0 THEN 1 ELSE 0 END) STORED,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    droplet_id INT NOT NULL DEFAULT 0,
    share_tag TEXT UNIQUE
)
""")

cur.execute("""
CREATE TRIGGER IF NOT EXISTS set_share_tag_after_insert
AFTER INSERT ON game_droplets
FOR EACH ROW
WHEN NEW.share_tag IS NULL
BEGIN
    UPDATE game_droplets
    SET share_tag = substr(hex(randomblob(3)), 1, 6)
    WHERE rowid = NEW.rowid;
END;
""")

conn.commit()
conn.close()

print("Database created: femquest.db")