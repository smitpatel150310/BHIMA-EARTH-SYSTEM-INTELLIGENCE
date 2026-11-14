import pytest
import pandas as pd
import numpy as np
from app.core.analysis import ScientificAnalysisEngine, AnalysisError

engine = ScientificAnalysisEngine()


def make_df(values, start="2010-01"):
    months = pd.date_range(start=start, periods=len(values), freq="MS")
    return pd.DataFrame({
        "date": [m.strftime("%Y-%m") for m in months],
        "value": values,
        "valid_pixels": [100] * len(values),
        "coverage_fraction": [1.0] * len(values)
    })


def test_descriptive_stats_basic():
    df = make_df([1.0, 2.0, 3.0, 4.0, 5.0])
    stats = engine.compute_descriptive_stats(df)
    assert stats["mean"] == pytest.approx(3.0)
    assert stats["n_valid"] == 5
    assert stats["n_missing"] == 0


def test_descriptive_stats_missing():
    df = make_df([1.0, None, 3.0, None, 5.0])
    stats = engine.compute_descriptive_stats(df)
    assert stats["n_valid"] == 3
    assert stats["n_missing"] == 2


def test_validation_no_duplicates():
    df = make_df([10.0, 20.0, 30.0])
    issues = engine.validate_timeseries(df)
    assert all("duplicate" not in i.lower() for i in issues)


def test_trend_increasing():
    # Strong increasing trend
    values = [float(i) + float(np.random.normal(0, 0.1)) for i in range(60)]
    df = make_df(values)
    trend = engine.compute_mann_kendall_trend(df)
    assert trend["trend_direction"] == "increasing"
    assert trend["slope"] > 0


def test_trend_decreasing():
    values = [float(60 - i) + float(np.random.normal(0, 0.1)) for i in range(60)]
    df = make_df(values)
    trend = engine.compute_mann_kendall_trend(df)
    assert trend["trend_direction"] == "decreasing"
    assert trend["slope"] < 0


def test_trend_minimum_observations():
    df = make_df([1.0] * 5)  # Only 5 obs, need 10
    with pytest.raises(AnalysisError):
        engine.compute_mann_kendall_trend(df)


def test_annual_aggregation():
    # 24 months = 2 years
    values = [100.0] * 24
    df = make_df(values, start="2010-01")
    annual = engine.compute_annual_means(df)
    assert len(annual) == 2
    assert annual.iloc[0]["annual_mean"] == pytest.approx(100.0)


def test_full_analysis_pipeline():
    values = [float(i * 2 + 50) for i in range(60)]
    df = make_df(values)
    result = engine.run_full_analysis(
        df=df,
        dataset_id="GPM_3IMERGM_07",
        variable="precipitation",
        units="mm/month",
        region_name="Test Region",
        source_description="Test",
        processing_notes=[]
    )
    assert "analysis_id" in result
    assert "timeseries" in result
    assert "trend" in result
    assert "statistics" in result
    assert result["trend"]["trend_direction"] == "increasing"
