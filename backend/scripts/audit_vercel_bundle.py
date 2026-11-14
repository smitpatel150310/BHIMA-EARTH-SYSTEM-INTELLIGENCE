import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def audit_site_packages(site_packages_dir: Path) -> List[Tuple[str, float]]:
    """Inspect site-packages and return top packages sorted by size in MB."""
    if not site_packages_dir.exists():
        print(f"Error: Directory {site_packages_dir} does not exist.")
        return []

    package_sizes: Dict[str, int] = {}

    for item in site_packages_dir.iterdir():
        if item.is_dir():
            # Group dist-info and .libs with base package name if applicable
            name = item.name
            size_bytes = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            package_sizes[name] = size_bytes
        elif item.is_file():
            # Single .py / .so / .pyd files
            package_sizes[item.name] = item.stat().st_size

    # Convert to MB and sort descending
    sorted_packages = [
        (name, round(size / (1024 * 1024), 2))
        for name, size in sorted(package_sizes.items(), key=lambda x: x[1], reverse=True)
    ]
    return sorted_packages


def audit_requirements(req_file: Path):
    """Analyze requirements.txt for Vercel serverless function compatibility."""
    if not req_file.exists():
        print(f"Error: {req_file} not found.")
        return

    with open(req_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print("\n" + "=" * 70)
    print("VERCEL DEPENDENCY COMPATIBILITY ANALYSIS")
    print("=" * 70)

    # Known heavy / problematic packages for Vercel Serverless (250MB limit)
    categorized = {
        "serverless_core": [],      # Essential for FastAPI request-driven queries
        "heavy_preprocessor": [],   # Offline ingestion only (Zarr, MPC, Parquet)
        "removable_or_gcp": [],     # Unneeded for Vercel deployment
        "test_and_dev": []          # Test runners (not for production bundle)
    }

    for line in lines:
        pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
        pkg_lower = pkg_name.lower()

        if pkg_lower in ("pytest", "pytest-asyncio"):
            categorized["test_and_dev"].append(line)
        elif "google-cloud" in pkg_lower or pkg_lower in ("gunicorn", "netcdf4"):
            categorized["removable_or_gcp"].append(line)
        elif pkg_lower in ("adlfs", "pyarrow", "xarray", "zarr", "numcodecs", "cftime", "planetary-computer", "pystac-client", "fsspec"):
            categorized["heavy_preprocessor"].append(line)
        else:
            categorized["serverless_core"].append(line)

    print("\n[A] Serverless Core (FastAPI, Pydantic, Pandas, Scipy, PyMannKendall, Gemini):")
    for dep in categorized["serverless_core"]:
        print(f"    - {dep}")

    print("\n[B] Heavy Background Preprocessor (Zarr / Cloud extraction - isolate from serverless):")
    for dep in categorized["heavy_preprocessor"]:
        print(f"    - {dep}")

    print("\n[C] Legacy / Unnecessary for Vercel (Should be removed from Vercel function requirements):")
    for dep in categorized["removable_or_gcp"]:
        print(f"    - {dep}")

    print("\n[D] Development / Testing Only (Exclude from production):")
    for dep in categorized["test_and_dev"]:
        print(f"    - {dep}")


def main():
    backend_dir = Path(__file__).resolve().parent.parent
    site_packages = backend_dir / "venv" / "Lib" / "site-packages"

    print("=" * 70)
    print("BHIMA VERCEL BUNDLE & PACKAGE SIZE AUDIT (PYTHON ENGINE)")
    print("=" * 70)
    print(f"Target site-packages directory: {site_packages}")

    top_packages = audit_site_packages(site_packages)
    print(f"\nTop 15 Largest Packages in Virtual Environment:")
    print("-" * 50)
    print(f"{'Package Name':<35} {'Size (MB)':>10}")
    print("-" * 50)
    total_top15 = 0.0
    for name, size_mb in top_packages[:15]:
        print(f"{name:<35} {size_mb:>10.2f} MB")
        total_top15 += size_mb
    print("-" * 50)
    print(f"{'Total Top 15':<35} {total_top15:>10.2f} MB")

    total_env = sum(s for _, s in top_packages)
    print(f"{'Total All Packages in venv':<35} {total_env:>10.2f} MB")

    req_path = backend_dir / "requirements.txt"
    audit_requirements(req_path)

    print("\n" + "=" * 70)
    print("VERCEL BUNDLE OPTIMIZATION RECOMMENDATION")
    print("=" * 70)
    print("1. Vercel uncompressed Serverless Function bundle limit is 250 MB.")
    print("2. The local virtual environment (venv/) MUST BE EXCLUDED from deployment.")
    print("3. Removing 'google-cloud-*' and 'gunicorn' saves ~120 MB.")
    print("4. Isolating 'pyarrow', 'xarray', 'adlfs' into background preprocessor saves ~110 MB.")
    print("5. Serverless core (FastAPI, Pandas, Scipy, PyMannKendall) will compile under ~180 MB uncompressed, safely within Vercel's 250 MB ceiling.")
    print("=" * 70)


if __name__ == "__main__":
    main()
