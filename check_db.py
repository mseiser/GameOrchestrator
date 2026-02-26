import sqlite3

conn = sqlite3.connect('db\\femquest.db')
cur = conn.cursor()

# Get table schema
result = cur.execute("SELECT sql FROM sqlite_master WHERE name='game_droplets'").fetchone()
if result:
    print("Table schema:")
    print(result[0])
else:
    print("Table not found")

# Get all columns
cur.execute("PRAGMA table_info(game_droplets)")
columns = cur.fetchall()
print("\nColumns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
