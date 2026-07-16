"""Run a generic VADM backtest: python run_backtest.py HDFCBANK path/to/fundamentals.xlsx"""

from __future__ import annotations
import sys
from vadm.config import StrategyConfig
from vadm.fundamentals import attach_point_in_time_pe, extract_annual_fundamentals
from vadm.market_data import fetch_eod2
from vadm.features import build_features
from vadm.backtest import run_backtest


def main(symbol: str, workbook: str) -> None:
    config = StrategyConfig()
    annual = extract_annual_fundamentals(workbook)
    market = fetch_eod2(symbol)
    data = build_features(attach_point_in_time_pe(market, annual, config.filing_lag_days), config)
    result = run_backtest(data, config)
    print({key: round(value, 4) if isinstance(value, float) else value for key, value in result.metrics.items()})
    if not result.trades.empty: print(result.trades.to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) != 3: raise SystemExit("Usage: python run_backtest.py SYMBOL FUNDAMENTALS.xlsx")
    main(sys.argv[1], sys.argv[2])
