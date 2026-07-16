"""Point-in-time features; no full-sample percentile ranks are used."""

from __future__ import annotations

import numpy as np
import pandas as pd
from .config import StrategyConfig


def expanding_percentile(series: pd.Series, min_periods: int) -> pd.Series:
    return series.expanding(min_periods=min_periods).apply(lambda window: window.rank(pct=True).iloc[-1], raw=False)


def _atr(data: pd.DataFrame, window: int) -> pd.Series:
    previous = data["close"].shift()
    true_range = pd.concat([data["high"] - data["low"], (data["high"] - previous).abs(), (data["low"] - previous).abs()], axis=1).max(axis=1)
    return true_range.rolling(window, min_periods=window).mean()


def build_features(data: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    out = data.copy()
    out["pe_percentile"] = expanding_percentile(out["pe"], config.percentile_lookback)
    out["delivery_percentile"] = expanding_percentile(out["delivery_pct"], config.percentile_lookback)
    out["delivery_flow"] = 2 * (out["delivery_percentile"] - 0.5)
    multiplier = np.where(out["delivery_flow"] >= 0, 1 - out["pe_percentile"], out["pe_percentile"])
    out["vadm"] = out["delivery_flow"] * multiplier
    out["vadm_percentile"] = expanding_percentile(out["vadm"], config.percentile_lookback)
    out["sma_fast"] = out["close"].rolling(20, min_periods=20).mean()
    out["sma_entry"] = out["close"].rolling(config.entry_sma_window, min_periods=config.entry_sma_window).mean()
    out["atr"] = _atr(out, config.atr_window)
    out["value_confirmation"] = (out["pe_percentile"] <= config.cheap_pe_percentile) & (out["delivery_percentile"] >= config.high_delivery_percentile)
    out["entry_signal"] = (out["value_confirmation"] & (out["vadm_percentile"] >= config.vadm_entry_percentile) & (out["close"] > out["sma_entry"])).fillna(False)
    out["entry_onset"] = out["entry_signal"] & ~out["entry_signal"].shift(fill_value=False)
    # A single weak day must not churn the position. Exit requires valuation-flow
    # deterioration *and* loss of the short trend, then executes next open.
    out["exit_signal"] = ((out["vadm_percentile"] <= config.vadm_exit_percentile) & (out["delivery_percentile"] < 0.5) & (out["close"] < out["sma_fast"])).fillna(False)
    return out
