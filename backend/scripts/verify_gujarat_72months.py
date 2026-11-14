import sys
import os
import sqlite3
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.persistent_cache import persistent_store, get_region_key
from app.core.data_access import NASADataAccessor
from app.core.analysis import ScientificAnalysisEngine

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "bhima_observations.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

reg_key = "73.10_22.10_73.30_22.50"
cur.execute("SELECT count(*), min(date), max(date) FROM regional_monthly WHERE dataset_id = 'GPM_3IMERGM_07' AND region_key = ?", (reg_key,))
row = cur.fetchone()
print(f"Region {reg_key}: {row[0]} months cached (from {row[1]} to {row[2]})")

# Check all 72 months
cached_recs, missing_months, audit = persistent_store.get_monthly_series(
    dataset_id="GPM_3IMERGM_07",
    region_key=reg_key,
    start_date="2015-01",
    end_date="2020-12",
    variable="precipitationCal"
)
print(f"Persistent Store Query: {len(cached_recs)} cached records, {len(missing_months)} missing months. Lookup time: {audit['lookup_duration_ms']:.3f} ms. Cache Status: {audit['cache_status']}")

# Run full analysis
accessor = NASADataAccessor()
engine = ScientificAnalysisEngine()

df, notes, provenance, src, c_audit = accessor.get_timeseries_data(
    dataset_id="GPM_3IMERGM_07",
    min_lon=73.10,
    max_lon=73.30,
    min_lat=22.10,
    max_lat=22.50,
    start_date="2015-01",
    end_date="2020-12"
)

result = engine.run_full_analysis(
    df=df,
    dataset_id="GPM_3IMERGM_07",
    variable="precipitation",
    units="mm/month",
    region_name="Gujarat, India",
    source_description="GPM IMERG",
    processing_notes=notes,
    data_provenance=provenance,
    data_source=src,
    cache_audit=c_audit,
)

print("\n--- ANALYSIS RESULT SUMMARY ---")
print(f"Analysis ID: {result['analysis_id']}")
print(f"Data Points: {len(result['timeseries']['data'])}")
print(f"Cache Status: {result['cache_status']} (Cache Hit: {result['cache_hit']})")
print(f"Lookup Duration: {result['lookup_duration_ms']} ms")
print(f"Provenance: {result['data_provenance']}")
print(f"Data Source: {result['data_source']}")
print(f"Descriptive Stats: Mean={result['statistics']['mean']:.2f} mm/month, Std={result['statistics']['std']:.2f}, Max={result['statistics']['max']:.2f}")
if result.get("trend") and "slope" in result["trend"]:
    print(f"Trend Direction: {result['trend']['trend_direction']}, Sen's Slope: {result['trend']['slope']:.4f} {result['trend']['slope_units']}, p-value: {result['trend']['p_value']:.4f}")
print("--- VERIFICATION COMPLETE ---")
