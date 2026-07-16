"""Stock-agnostic Valuation Adjusted Delivery Momentum research engine."""

from .config import StrategyConfig
from .backtest import BacktestResult, run_backtest
from .features import build_features

__all__ = ["BacktestResult", "StrategyConfig", "build_features", "run_backtest"]
