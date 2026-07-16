"""Market-data adapters. Delivery data is required; failures are explicit."""

from __future__ import annotations

from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import pandas as pd

EOD2_URL = "https://raw.githubusercontent.com/BennyThadikaran/eod2_data/main/daily/{symbol}.csv"


def fetch_eod2(symbol: str, timeout: int = 30) -> pd.DataFrame:
    symbol = symbol.strip().upper().replace(".NS", "")
    try:
        response = urlopen(EOD2_URL.format(symbol=symbol.lower()), timeout=timeout)
        text = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ValueError(f"Delivery-enabled data unavailable for {symbol} (HTTP {exc.code}). Upload a compatible data file or choose another symbol.") from exc
    except URLError as exc:
        raise ValueError(f"Could not reach the delivery-data source: {exc.reason}") from exc
    raw = pd.read_csv(StringIO(text), parse_dates=["Date"]).set_index("Date").sort_index()
    required = {"Open", "High", "Low", "Close", "Volume", "DLV_QTY"}
    missing = required - set(raw.columns)
    if missing: raise ValueError(f"Market data is missing required fields: {sorted(missing)}")
    out = raw.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume", "DLV_QTY": "delivery_qty"})
    out["delivery_pct"] = 100 * pd.to_numeric(out["delivery_qty"], errors="coerce") / pd.to_numeric(out["volume"], errors="coerce").replace(0, pd.NA)
    out.loc[(out["delivery_pct"] < 0) | (out["delivery_pct"] > 100), "delivery_pct"] = pd.NA
    out = out[["open", "high", "low", "close", "volume", "delivery_qty", "delivery_pct"]].apply(pd.to_numeric, errors="coerce").dropna(subset=["open", "high", "low", "close"])
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out
