import os
import sqlite3

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "bhima_observations.db"))
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM regional_monthly")
total = cursor.fetchone()[0]

cursor.execute("SELECT dataset_id, region_key, COUNT(*), MIN(date), MAX(date) FROM regional_monthly GROUP BY dataset_id, region_key ORDER BY dataset_id, region_key")
rows = cursor.fetchall()

print("================ CACHE SUMMARY (READ-ONLY DIRECT) ================")
print(f"Total SQLite Records: {total}")
print(f"DB File: {db_path} ({os.path.getsize(db_path)/1024:.1f} KB)")
print("------------------------------------------------------------------")
for r in rows:
    comp = "72/72 COMPLETE" if r[2] == 72 else f"{r[2]}/72 PARTIAL"
    print(f"{r[0]:<18} | {r[1]:<28} | {comp} | Range: {r[3]} to {r[4]}")
print("==================================================================")
conn.close()
