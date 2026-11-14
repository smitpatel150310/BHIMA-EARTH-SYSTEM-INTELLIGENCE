import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
import pymannkendall as mk

logger = logging.getLogger(__name__)

MIN_OBSERVATIONS_FOR_TREND = 10


class AnalysisError(Exception):
    pass


class ScientificAnalysisEngine:
    """
    Statistically rigorous analysis of environmental time series.
    All methods are deterministic and reproducible from input data.
    """

    def validate_timeseries(self, df: pd.DataFrame) -> List[str]:
        """Validate a timeseries DataFrame. Returns list of issues found."""
        issues = []
        required_cols = {"date", "value"}
        if not required_cols.issubset(df.columns):
            issues.append(f"Missing required columns: {required_cols - set(df.columns)}")
            return issues

        # Check for duplicates
        dups = df["date"].duplicated().sum()
        if dups > 0:
            issues.append(f"Found {dups} duplicate timestamps")

        # Check date parsing
        try:
            pd.to_datetime(df["date"])
        except Exception as e:
            issues.append(f"Date parsing error: {e}")

        # Check temporal ordering
        dates = pd.to_datetime(df["date"])
        if not dates.is_monotonic_increasing:
            issues.append("Timestamps are not monotonically increasing")

        # Check value range for precipitation (can't be negative)
        valid_vals = df["value"].dropna()
        if len(valid_vals) == 0:
            issues.append("All values are missing")
        elif valid_vals.min() < -0.001:
            issues.append(f"Found {(valid_vals < 0).sum()} negative precipitation values")

        # Missing data report
        n_missing = df["value"].isna().sum()
        if n_missing > 0:
            pct = n_missing / len(df) * 100
            issues.append(f"Missing: {n_missing}/{len(df)} ({pct:.1f}%)")

        return issues

    def compute_descriptive_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute descriptive statistics on valid values."""
        valid = df["value"].dropna()
        if len(valid) == 0:
            return {"error": "No valid observations"}

        std_val = float(valid.std()) if len(valid) > 1 else 0.0
        mean_val = float(valid.mean())

        return {
            "n_total": int(len(df)),
            "n_valid": int(len(valid)),
            "n_missing": int(len(df) - len(valid)),
            "mean": mean_val,
            "median": float(valid.median()),
            "std": std_val,
            "min": float(valid.min()),
            "max": float(valid.max()),
            "q25": float(valid.quantile(0.25)),
            "q75": float(valid.quantile(0.75)),
            "cv": float(std_val / mean_val) if mean_val != 0 else None,
        }

    def compute_annual_means(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate monthly data to annual means."""
        df = df.copy()
        df["year"] = pd.to_datetime(df["date"]).dt.year
        annual = df.groupby("year")["value"].agg(["mean", "count", "std"]).reset_index()
        annual.columns = ["year", "annual_mean", "n_months", "std"]
        # Only use years with at least 6 months
        annual = annual[annual["n_months"] >= 6]
        return annual

    def compute_mann_kendall_trend(
        self,
        df: pd.DataFrame,
        significance_level: float = 0.05
    ) -> Dict[str, Any]:
        """
        Mann-Kendall trend test + Sen's slope.
        Uses pymannkendall with pre-whitening to reduce autocorrelation bias.
        Falls back to original test if Hamed-Rao modification results in NaN (e.g. perfect linear fit).
        Returns full trend result dict.
        """
        valid = df["value"].dropna()

        if len(valid) < MIN_OBSERVATIONS_FOR_TREND:
            raise AnalysisError(
                f"Insufficient observations for trend analysis: "
                f"{len(valid)} < {MIN_OBSERVATIONS_FOR_TREND} required"
            )

        x = valid.values.astype(float)

        # Use pre-whitened Mann-Kendall to handle autocorrelation
        try:
            result = mk.hamed_rao_modification_test(x)
            if np.isnan(result.p) or np.isnan(result.z):
                result = mk.original_test(x)
        except Exception:
            # Fallback to original MK if pre-whitening fails
            result = mk.original_test(x)

        # Sen's slope (robust, non-parametric)
        sen_slope_per_step = result.slope  # per time step (month)
        sen_slope_per_year = sen_slope_per_step * 12  # convert to per year

        # Period information
        valid_dates = df.loc[df["value"].notna(), "date"].reset_index(drop=True)
        period_start = valid_dates.iloc[0] if len(valid_dates) > 0 else "unknown"
        period_end = valid_dates.iloc[-1] if len(valid_dates) > 0 else "unknown"

        # Trend direction
        if result.p <= significance_level:
            if result.slope > 0:
                direction = "increasing"
            elif result.slope < 0:
                direction = "decreasing"
            else:
                direction = "no_trend"
        else:
            direction = "no_trend"

        # Human interpretation
        if direction == "increasing":
            interp = (
                f"A statistically significant increasing trend is detected "
                f"(Sen's slope: +{sen_slope_per_year:.3f} units/year, "
                f"p={result.p:.4f}). "
                f"The trend is based on {len(valid)} observations from {period_start} to {period_end}."
            )
        elif direction == "decreasing":
            interp = (
                f"A statistically significant decreasing trend is detected "
                f"(Sen's slope: {sen_slope_per_year:.3f} units/year, "
                f"p={result.p:.4f}). "
                f"The trend is based on {len(valid)} observations from {period_start} to {period_end}."
            )
        else:
            interp = (
                f"No statistically significant trend detected "
                f"(p={result.p:.4f} > {significance_level}). "
                f"The analysis used {len(valid)} observations from {period_start} to {period_end}. "
                f"Absence of a significant trend does not confirm that no change occurred."
            )

        limitations = [
            "Mann-Kendall assumes data independence; modified test reduces but does not eliminate autocorrelation bias.",
            "Statistical significance depends on sample size; short records may underpower the test.",
            "Spatial averaging over bounding box may mask local heterogeneity.",
            "Satellite-derived precipitation estimates carry retrieval uncertainty.",
        ]

        # Approximate 95% CI for Sen's slope using percentile bootstrap
        try:
            ci_low, ci_high = self._bootstrap_sen_ci(x, n_boot=100)
            ci_low_yr = ci_low * 12
            ci_high_yr = ci_high * 12
        except Exception:
            ci_low_yr = None
            ci_high_yr = None

        tau_val = getattr(result, "Tau", getattr(result, "tau", 0.0))

        return {
            "method": "Hamed-Rao Modified Mann-Kendall Test + Sen's Slope",
            "slope": float(sen_slope_per_year),
            "slope_units": "units/year",
            "p_value": float(result.p),
            "is_significant": bool(result.p <= significance_level),
            "significance_level": significance_level,
            "trend_direction": direction,
            "confidence_interval_low": float(ci_low_yr) if ci_low_yr is not None else None,
            "confidence_interval_high": float(ci_high_yr) if ci_high_yr is not None else None,
            "n_observations": int(len(valid)),
            "period_start": str(period_start),
            "period_end": str(period_end),
            "interpretation": interp,
            "limitations": limitations,
            "tau": float(tau_val),
            "s": float(result.s),
            "var_s": float(result.var_s),
            "z": float(result.z),
        }

    def _bootstrap_sen_ci(
        self, x: np.ndarray, n_boot: int = 100, ci: float = 0.95
    ) -> Tuple[float, float]:
        """Bootstrap 95% CI for Sen's slope."""
        rng = np.random.default_rng(42)
        slopes = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(x), size=len(x))
            sample = x[idx]
            try:
                r = mk.original_test(sample)
                slopes.append(r.slope)
            except Exception:
                pass

        if not slopes:
            raise ValueError("Bootstrap failed")

        alpha = (1 - ci) / 2
        return float(np.quantile(slopes, alpha)), float(np.quantile(slopes, 1 - alpha))

    def run_full_analysis(
        self,
        df: pd.DataFrame,
        dataset_id: str,
        variable: str,
        units: str,
        region_name: str,
        source_description: str,
        processing_notes: List[str],
        data_provenance: str = "REAL_NASA_DATA",
        data_source: Optional[str] = None,
        cache_audit: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run complete analysis pipeline on a timeseries DataFrame."""
        analysis_id = str(uuid.uuid4())[:8]
        computed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        cache_status = cache_audit.get("cache_status", "MISS") if cache_audit else "MISS"
        cache_hit = cache_audit.get("cache_hit", False) if cache_audit else False
        lookup_ms = float(cache_audit.get("lookup_duration_ms", 0.0)) if cache_audit else 0.0
        storage_type = cache_audit.get("storage_type", "SQLite") if cache_audit else "SQLite"

        validation_issues = self.validate_timeseries(df)
        stats = self.compute_descriptive_stats(df)

        trend = None
        valid_count = int(df["value"].notna().sum())

        if valid_count >= MIN_OBSERVATIONS_FOR_TREND:
            try:
                trend = self.compute_mann_kendall_trend(df)
                trend["slope_units"] = f"{units}/year"
                trend["interpretation"] = trend["interpretation"].replace("units/year", f"{units}/year")
            except AnalysisError as e:
                trend = {"error": str(e)}
            except Exception as e:
                logger.error(f"Trend analysis failed: {e}")
                trend = {"error": f"Analysis failed: {str(e)}"}
        else:
            trend = {"error": f"Insufficient valid observations: {valid_count} < {MIN_OBSERVATIONS_FOR_TREND}"}

        # Build data points list
        data_points = []
        for _, row in df.iterrows():
            data_points.append({
                "date": row["date"],
                "value": float(row["value"]) if pd.notna(row["value"]) else None,
                "valid_pixels": int(row.get("valid_pixels", 0)) if pd.notna(row.get("valid_pixels")) else None,
                "coverage_fraction": float(row.get("coverage_fraction", 0)) if pd.notna(row.get("coverage_fraction")) else None,
            })

        return {
            "analysis_id": analysis_id,
            "timeseries": {
                "dataset_id": dataset_id,
                "variable": variable,
                "units": units,
                "region": region_name,
                "start_date": df["date"].iloc[0] if len(df) > 0 else "",
                "end_date": df["date"].iloc[-1] if len(df) > 0 else "",
                "temporal_resolution": "monthly",
                "data": data_points,
                "n_valid": valid_count,
                "n_missing": int(df["value"].isna().sum()),
                "retrieval_timestamp": computed_at,
                "source_description": source_description,
                "processing_notes": processing_notes,
                "validation_issues": validation_issues,
                "data_provenance": data_provenance,
                "data_source": data_source or "Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
                "cache_status": cache_status,
                "cache_hit": cache_hit,
                "lookup_duration_ms": lookup_ms,
                "storage_type": storage_type,
            },
            "trend": trend,
            "statistics": stats,
            "methodology": (
                "Regional time series extracted by spatial averaging over bounding box. "
                "Trend analyzed using Hamed-Rao Modified Mann-Kendall test to account for "
                "serial autocorrelation. Sen's slope provides a robust non-parametric "
                "estimate of the trend magnitude."
            ),
            "computed_at": computed_at,
            "data_provenance": data_provenance,
            "data_source": data_source or "Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
            "cache_status": cache_status,
            "cache_hit": cache_hit,
            "lookup_duration_ms": lookup_ms,
            "storage_type": storage_type,
        }
