from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyConfig:
    """Defaults are inputs, not stock-specific constants; all can be changed in the UI."""

    percentile_lookback: int = 252
    cheap_pe_percentile: float = 0.35
    high_delivery_percentile: float = 0.70
    vadm_entry_percentile: float = 0.90
    vadm_exit_percentile: float = 0.35
    entry_sma_window: int = 50
    atr_window: int = 14
    stop_atr_multiple: float = 2.0
    trailing_atr_multiple: float = 3.0
    max_holding_days: int = 63
    commission_bps: float = 10.0
    slippage_bps: float = 5.0
    filing_lag_days: int = 60
