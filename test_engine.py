import numpy as np
import pandas as pd
from vadm.config import StrategyConfig
from vadm.features import build_features
from vadm.backtest import run_backtest


def sample_data(rows=320):
    index = pd.bdate_range("2023-01-02", periods=rows)
    close = pd.Series(np.linspace(100, 150, rows), index=index)
    return pd.DataFrame({"open": close, "high": close + 2, "low": close - 2, "close": close, "volume": 1000, "delivery_qty": 600, "delivery_pct": np.linspace(35, 85, rows), "pe": np.linspace(30, 10, rows)}, index=index)


def test_features_are_point_in_time_and_backtest_runs():
    config = StrategyConfig(percentile_lookback=30)
    data = build_features(sample_data(), config)
    assert data.vadm_percentile.iloc[:29].isna().all()
    result = run_backtest(data, config)
    assert {"trades", "total_return", "max_drawdown"}.issubset(result.metrics)
