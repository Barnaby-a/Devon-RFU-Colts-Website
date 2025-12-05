import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'app.db')
DB_PATH = os.path.abspath(DB_PATH)

print('Using DB at:', DB_PATH)
if not os.path.exists(DB_PATH):
    print('Database file not found at', DB_PATH)
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# get existing columns in team table
cur.execute("PRAGMA table_info('team')")
cols = [r[1] for r in cur.fetchall()]
print('Existing columns:', cols)

added = False
if 'player_code' not in cols:
    try:
        cur.execute("ALTER TABLE team ADD COLUMN player_code VARCHAR(64);")
        print('Added column player_code')
        added = True
    except Exception as e:
        print('Failed to add player_code:', e)

if 'coach_code' not in cols:
    try:
        cur.execute("ALTER TABLE team ADD COLUMN coach_code VARCHAR(64);")
        print('Added column coach_code')
        added = True
    except Exception as e:
        print('Failed to add coach_code:', e)

if added:
    conn.commit()
    print('Committed schema changes')
else:
    print('No schema changes required')

conn.close()
print('Done')
