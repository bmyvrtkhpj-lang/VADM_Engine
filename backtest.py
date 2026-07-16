"""Long-only, next-open backtest with gap-aware stops and trade-level audit data."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
from .config import StrategyConfig


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: dict[str, float]


def _buy_price(open_price: float, config: StrategyConfig) -> float:
    return open_price * (1 + (config.commission_bps + config.slippage_bps) / 10_000)


def _sell_price(price: float, config: StrategyConfig) -> float:
    return price * (1 - (config.commission_bps + config.slippage_bps) / 10_000)


def run_backtest(data: pd.DataFrame, config: StrategyConfig) -> BacktestResult:
    required = {"open", "high", "low", "close", "atr", "entry_onset", "exit_signal"}
    if missing := required - set(data.columns): raise ValueError(f"Missing backtest columns: {sorted(missing)}")
    trades, equity_rows, position, pending = [], [], None, None
    equity = 1.0
    for index, row in data.iterrows():
        if position is None and pending == "enter" and pd.notna(row["open"]):
            position = {"entry_date": index, "entry_price": _buy_price(float(row["open"]), config), "peak": float(row["high"]), "bars": 0}
            pending = None
        elif position is not None and pending == "exit":
            exit_price = _sell_price(float(row["open"]), config)
            gross = exit_price / position["entry_price"] - 1
            equity *= 1 + gross
            trades.append({**position, "exit_date": index, "exit_price": exit_price, "return": gross, "reason": "signal_exit"})
            position, pending = None, None
        if position is not None:
            position["bars"] += 1
            position["peak"] = max(position["peak"], float(row["high"]))
            if pd.notna(row["atr"]):
                stop = max(position["entry_price"] - config.stop_atr_multiple * float(row["atr"]), position["peak"] - config.trailing_atr_multiple * float(row["atr"]))
                if float(row["low"]) <= stop:
                    exit_price = _sell_price(min(float(row["open"]), stop), config)
                    gross = exit_price / position["entry_price"] - 1
                    equity *= 1 + gross
                    trades.append({**position, "exit_date": index, "exit_price": exit_price, "return": gross, "reason": "atr_stop"})
                    position, pending = None, None
            if position is not None and (bool(row["exit_signal"]) or position["bars"] >= config.max_holding_days): pending = "exit"
        if position is None and pending is None and bool(row["entry_onset"]): pending = "enter"
        marked_equity = equity if position is None else equity * float(row["close"]) / position["entry_price"]
        equity_rows.append({"date": index, "equity": marked_equity, "in_position": position is not None})
    trade_frame = pd.DataFrame(trades)
    curve = pd.DataFrame(equity_rows).set_index("date")
    if trade_frame.empty:
        metrics = {"trades": 0, "win_rate": 0.0, "total_return": 0.0, "max_drawdown": 0.0}
    else:
        drawdown = curve["equity"] / curve["equity"].cummax() - 1
        metrics = {"trades": int(len(trade_frame)), "win_rate": float((trade_frame["return"] > 0).mean()), "total_return": float(curve["equity"].iloc[-1] - 1), "max_drawdown": float(drawdown.min())}
    return BacktestResult(trades=trade_frame, equity_curve=curve, metrics=metrics)
