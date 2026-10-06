#!/bin/sh
docker exec femquest-orchestrator-api python3 - <<'EOF'
import sqlite3

DB = "/data/physicsquest_measurements.db"
conn = sqlite3.connect(DB)

total = conn.execute("SELECT COUNT(*) FROM measurement_events").fetchone()[0]
print(f"\n=== Measurements DB  ({total} events total) ===\n")

print("-- Sessions overview --")
rows = conn.execute("""
    SELECT share_tag,
           COUNT(DISTINCT client_id) AS clients,
           COUNT(*)                  AS events,
           MIN(received_at)          AS first,
           MAX(received_at)          AS last
    FROM measurement_events
    GROUP BY share_tag
    ORDER BY last DESC
""").fetchall()
for r in rows:
    print(f"  share_tag={r[0]}  clients={r[1]}  events={r[2]}  {r[3]} -> {r[4]}")

print("\n-- Last 20 events --")
rows = conn.execute("""
    SELECT id, client_id, share_tag, event_type, event_timestamp, payload
    FROM measurement_events
    ORDER BY id DESC
    LIMIT 20
""").fetchall()
for r in rows:
    print(f"  [{r[0]:>4}] {r[3]:30s}  share={r[2]}  client={r[1][:8]}  payload={r[5]}")

conn.close()
EOF
