"""Yahoo Finance pieces of the long-term layer: ten years of weekly prices with splits and dividends, and (for India, where
there are no SEC filings) the company's annual and quarterly statements from Yahoo's fundamentals feed. Yahoo is not an
official source, so every screen that uses it says so."""
import time
import urllib.parse

import pandas as pd

from us import market as M

ANNUAL = {"TotalRevenue": "revenue", "GrossProfit": "gross", "OperatingIncome": "opinc", "NetIncome": "net", "OperatingCashFlow": "ocf",
          "CapitalExpenditure": "capex", "FreeCashFlow": "fcf", "StockholdersEquity": "equity", "TotalDebt": "debt",
          "CashAndCashEquivalents": "cash", "DilutedEPS": "eps", "DilutedAverageShares": "shares", "CashDividendsPaid": "div",
          "TotalAssets": "assets", "CurrentAssets": "cur_assets", "CurrentLiabilities": "cur_liab"}
MONEY = ("revenue", "gross", "opinc", "net", "ocf", "capex", "fcf", "equity", "debt", "cash", "div", "assets", "cur_assets", "cur_liab")


def weekly(sym_y, rng="10y"):
    """Weekly closes (split-adjusted by Yahoo), the splits and the dividends. Returns (DataFrame[close], splits, dividends, meta)."""
    d = M.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym_y)}?interval=1wk&range={rng}&events=div%2Csplits", 30)["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    df = pd.DataFrame({"close": q["close"], "high": q["high"], "low": q["low"]}, index=pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_localize(None).normalize()).dropna(subset=["close"])
    ev = d.get("events") or {}
    splits = sorted((pd.Timestamp(v["date"], unit="s").normalize(), v["numerator"] / v["denominator"]) for v in (ev.get("splits") or {}).values())
    divs = sorted((pd.Timestamp(v["date"], unit="s").normalize(), v["amount"]) for v in (ev.get("dividends") or {}).values())
    return df, splits, divs, d.get("meta") or {}


def unadjusted(df, splits):
    """Prices as they were quoted on the day: Yahoo splits-adjusts history, filings do not, so multiply back by the later splits."""
    f = pd.Series(1.0, index=df.index)
    for date, ratio in splits:
        f[f.index < date] *= ratio
    return df["close"] * f


def statements(sym_y):
    """Annual (about four years) and quarterly statements from Yahoo's fundamentals feed: {'annual': [...], 'quarterly': [...]}."""
    out = {}
    for pre, key in (("annual", "annual"), ("quarterly", "quarterly")):
        types = ",".join(pre + k for k in ANNUAL)
        d = M.get_json(f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{urllib.parse.quote(sym_y)}?type={types}&period1=1230768000&period2={int(time.time())}", 30)
        rows = {}
        for r in d["timeseries"]["result"]:
            t = r["meta"]["type"][0]
            name = ANNUAL.get(t[len(pre):])
            for x in r.get(t, []) or []:
                if x and x.get("reportedValue"):
                    rows.setdefault(x["asOfDate"], {"end": x["asOfDate"], "fy": x["asOfDate"][:4]})[name] = x["reportedValue"]["raw"]
        out[key] = [rows[k] for k in sorted(rows)]
    return out
