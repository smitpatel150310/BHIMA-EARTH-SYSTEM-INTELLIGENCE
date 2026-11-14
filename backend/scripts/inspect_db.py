import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "bhima_observations.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

for t in ["regional_monthly", "regional_daily", "regional_annual"]:
    if t in tables:
        count = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"\n{t}: {count} records")
        rows = cur.execute(f"SELECT dataset_id, region_key, count(*), min(date), max(date) FROM {t} GROUP BY dataset_id, region_key").fetchall()
        for r in rows:
            print("  ", r)
