"""Live tape for US Smart Money: every S&P 500 and Nasdaq-100 stock and the three indices (S&P 500, Nasdaq-100,
Dow), live. The US counterpart of sm/feed.py, same shapes, so the page draws it the same way.

Prices: Yahoo's batch "spark" endpoint (20 symbols a call, 1-minute closes since the open and the last price):
the indices every 4 seconds, every stock every 12 seconds. Daily bars per stock (once a day) give the previous
day's levels and a normal day's range. Structure, order blocks and gaps are read from 5-minute bars built out
of the 1-minute closes. Alpaca's free websocket can replace the polling later for true ticks."""
import threading
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from sm import feed as IN
from sm import smc
from . import market as M
from . import universe as U

INDICES = U.INDICES
STATE = {"stocks": {}, "indices": {}, "meta": {}, "daily": {}, "daily_idx": {}, "time": None, "errors": 0, "slow_until": 0}
GOT, LOCK = {}, threading.Lock()

# the sector chips on the tape: the 11 GICS sectors, shortened
CHIP = {"Information Technology": "TECH", "Financials": "FINANCIALS", "Health Care": "HEALTH CARE", "Consumer Discretionary": "DISCRETIONARY",
        "Consumer Staples": "STAPLES", "Energy": "ENERGY", "Industrials": "INDUSTRIALS", "Materials": "MATERIALS",
        "Real Estate": "REAL ESTATE", "Utilities": "UTILITIES", "Communication Services": "COMM SERVICES"}
SEMIS = {"Semiconductors", "Semiconductor Materials & Equipment"}


def chip(sym):
    v = U.U["list"].get(sym) or {}
    if v.get("sub") in SEMIS:
        return "SEMIS"
    if v.get("sub") in ("Application Software", "Systems Software"):
        return "SOFTWARE"
    return CHIP.get(v.get("sector"), "OTHERS")


def fetch(ysyms):
    for i in range(0, len(ysyms), 20):
        try:
            GOT.update(IN.spark(ysyms[i:i + 20]))
            STATE["errors"] = 0
        except Exception as e:
            STATE["errors"] += 1
            if "429" in str(e):
                STATE["slow_until"] = time.time() + 120
                return
        time.sleep(0.08)


def daily_bars(y, rng="3mo"):
    import urllib.parse
    d = M.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(y)}?interval=1d&range={rng}")["chart"]["result"][0]
    o = d["indicators"]["quote"][0]
    return pd.DataFrame({k: o[k] for k in ("open", "high", "low", "close", "volume")},
                        index=pd.to_datetime(d["timestamp"], unit="s", utc=True)).dropna(subset=["close"])


def load_daily(symbols, log=print):
    out, today = {}, M.now_et().date()
    for i, s in enumerate(symbols):
        try:
            df = daily_bars(s)
            past = df[[t.tz_convert(M.ET).date() < today for t in df.index]]
            if len(past) >= 15:
                rng = (past["high"] - past["low"]) / past["close"] * 100
                out[s] = {"pdh": float(past["high"].iloc[-1]), "pdl": float(past["low"].iloc[-1]),
                          "pdc": float(past["close"].iloc[-1]), "range": float(rng.iloc[-20:].mean())}
        except Exception as e:
            if "429" in str(e):
                log("Yahoo asked us to slow down; pausing 60 s")
                time.sleep(60)
        if i % 50 == 0:
            log(f"US daily levels {i}/{len(symbols)}")
        time.sleep(0.25)
    return out


def path(closes, base):
    if closes is None or not base:
        return []
    m, _ = M.session_minutes(closes.index)
    return [[int(a), round(float(b), 3)] for a, b in zip(m, (closes.values / base - 1) * 100) if 0 <= a <= M.SESSION_MIN]


def _read(df, daily=None):
    try:
        r = smc.read(df, 2, daily, M.ET, M.OPEN_MIN) if df is not None and len(df) >= 12 else None
    except Exception:
        return None
    if not r:
        return None
    st = r["structure"]["last"]
    return {"struct": st and {"type": st["type"], "dir": st["dir"], "time": st["time"]},
            "ob": (r["order_blocks"] or [None])[0], "fvg": (r["fvgs"] or [None])[0], "liq": r["liquidity"],
            "ev": [[int(M.session_minutes(pd.DatetimeIndex([pd.Timestamp(e["time"], unit="s", tz="UTC")]))[0][0]), 1 if e["dir"] == "bull" else -1]
                   for e in r["chart"]["events"] if e["time"] >= int(df.index[0].timestamp())]}


def cycle(stocks_too, structure):
    syms = list(STATE["meta"])
    fetch((syms if stocks_too else []) + list(INDICES.values()))
    now_m = M.minute_now()
    if stocks_too:
        stocks = {}
        for s in syms:
            g, meta, dly = GOT.get(s), STATE["meta"][s], STATE["daily"].get(s)
            if not g or not g.get("ltp"):
                continue
            ltp, prev = g["ltp"], g.get("prev")
            cl = g["closes"]
            opn = float(cl.iloc[0]) if len(cl) else None
            if not (ltp and prev and opn):
                continue
            fo = (ltp / opn - 1) * 100
            row = {"sym": s, "name": meta["name"], "sector": chip(s), "ltp": round(ltp, 2), "pct": round((ltp / prev - 1) * 100, 2),
                   "from_open": round(fo, 2), "disp": round(fo / ((dly or {}).get("range") or 2.0), 2), "path": path(cl, opn),
                   "value_cr": None, "ffmc": meta.get("mcap") or 0}
            b = IN.bars5(cl, opn)
            if b is not None:
                row["bars"] = [[round(float(x), 2) for x in r] for r in b[["open", "high", "low", "close"]].values]
            if dly:
                row["pdh"], row["pdl"] = round(dly["pdh"], 2), round(dly["pdl"], 2)
                hi = float(cl.max()) if len(cl) else 0
                lo = float(cl.min()) if len(cl) else 1e12
                row["liq"] = [k for k, hit in (("PDH", hi > dly["pdh"]), ("PDL", 0 < lo < dly["pdl"])) if hit]
            old = STATE["stocks"].get(s, {})
            if structure or "read" not in old:
                rd = _read(b)
                row["read"] = rd and {k: rd[k] for k in ("struct", "ob", "fvg", "ev")}
            else:
                row["read"] = old.get("read")
            p = row["path"]
            row["trail"] = next((v for m, v in reversed(p) if m <= now_m - 15), None) if p else None
            stocks[s] = row
        bull = sorted([r for r in stocks.values() if r["from_open"] > 0], key=lambda r: -r["disp"])
        bear = sorted([r for r in stocks.values() if r["from_open"] <= 0], key=lambda r: r["disp"])
        for i, r in enumerate(bull):
            r["rank"], r["side"] = i + 1, "bull"
        for i, r in enumerate(bear):
            r["rank"], r["side"] = i + 1, "bear"
    else:
        stocks = STATE["stocks"]
    idx = {}
    for k, y in INDICES.items():
        g = GOT.get(y)
        if not g or not g["ltp"]:
            continue
        cl = g["closes"]
        base = float(cl.iloc[0]) if len(cl) else g["ltp"]
        b = IN.bars5(cl, base)
        old = STATE["indices"].get(k, {})
        rd = _read(b, STATE["daily_idx"].get(k)) if structure or not old.get("read") else old.get("read")
        idx[k] = {"ltp": round(g["ltp"], 2), "pct": round((g["ltp"] / g["prev"] - 1) * 100, 2) if g["prev"] else None,
                  "from_open": round((g["ltp"] / base - 1) * 100, 2), "path": path(cl, base),
                  "bars": [[round(float(x), 2) for x in r] for r in b[["open", "high", "low", "close"]].values] if b is not None else [],
                  "read": rd, "expiry": next_expiry(k), "delay": int(time.time() - g["time"]) if g.get("time") and M.is_open() else None}
    with LOCK:
        STATE.update(stocks=stocks, indices=idx, time=datetime.now(timezone.utc).isoformat(timespec="seconds"))


def next_expiry(key):
    """Index options: the next Friday that trades (monthly = third Friday); shown on each index card like India's expiry."""
    d = M.now_et().date()
    for k in range(10):
        x = d + timedelta(days=k)
        if x.weekday() != 4:
            continue
        while not M.is_trading_day(x):
            x -= timedelta(days=1)
        if x >= d:
            return x.isoformat()
    return None


def snapshot(paths=True):
    with LOCK:
        stocks = list(STATE["stocks"].values())
        idx = dict(STATE["indices"])
    if not paths:
        stocks = [{k: v for k, v in r.items() if k != "path"} for r in stocks]
    secs = {}
    for r in stocks:
        secs.setdefault(r["sector"], []).append(r)
    sectors = sorted([{"name": k, "pct": round(float(np.mean([r["pct"] for r in v])), 2), "up": sum(r["pct"] > 0 for r in v),
                       "down": sum(r["pct"] < 0 for r in v), "n": len(v)} for k, v in secs.items()], key=lambda s: -s["pct"])
    return {"time": STATE["time"], "market": M.market_status(), "errors": STATE["errors"], "indices": idx, "stocks": stocks,
            "sectors": sectors, "bull": [r["sym"] for r in sorted(stocks, key=lambda r: r.get("rank", 999)) if r.get("side") == "bull"],
            "bear": [r["sym"] for r in sorted(stocks, key=lambda r: r.get("rank", 999)) if r.get("side") == "bear"]}


def ysym(sym):
    return INDICES.get(sym, sym if sym.startswith("^") else sym)


def quote(sym):
    import urllib.parse
    m = M.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ysym(sym))}?interval=1m&range=1d", 8)["chart"]["result"][0]["meta"]
    return {"ltp": m.get("regularMarketPrice"), "time": m.get("regularMarketTime"), "prev": m.get("chartPreviousClose")}


def chart(sym, tf="5m"):
    import urllib.parse
    rng = {"1m": "5d", "5m": "1mo", "15m": "60d", "60m": "2y", "1d": "5y"}[tf]
    y = ysym(sym)
    d = M.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(y)}?interval={tf}&range={rng}")["chart"]["result"][0]
    o = d["indicators"]["quote"][0]
    df = pd.DataFrame({k: o[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(d["timestamp"], unit="s", utc=True)).dropna(subset=["open", "high", "low", "close"])
    df["volume"] = df["volume"].fillna(0)
    daily = None
    if tf != "1d":
        try:
            daily = daily_bars(y)
        except Exception:
            pass
    rd = smc.read(df, 2 if tf in ("1m", "5m") else 3, daily, M.ET, M.OPEN_MIN) if len(df) >= 30 else None
    m = d["meta"]
    return {"sym": sym, "tf": tf, "ltp": m.get("regularMarketPrice"), "prev": prev_close(df, M.ET) or m.get("chartPreviousClose"),
            "candles": [{"time": int(t.timestamp()), "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume}
                        for t, r in df.iterrows()], "read": rd}



def prev_close(df, tz):
    """Yesterday's close, read from the bars themselves. Yahoo's chartPreviousClose is the close before the whole requested range began, which is years back on a daily chart."""
    try:
        if len(df) < 2:
            return None
        days = df.index.tz_convert(tz).date
        last = days[-1]
        prior = df["close"][days != last]
        return float(prior.iloc[-1]) if len(prior) else None
    except Exception:
        return None


def run(log=print):
    last = {"day": None, "stocks": 0, "struct": 0}
    while True:
        try:
            today = M.now_et().date()
            if last["day"] != today:
                U.load_lists()
                STATE["meta"] = {s: {"name": (U.U["list"].get(s) or {}).get("name") or s} for s in U.tape()}
                last["day"] = today
                log(f"{len(STATE['meta'])} US tape stocks; loading daily levels")
                STATE["daily_idx"] = {}
                for k, y in INDICES.items():
                    try:
                        STATE["daily_idx"][k] = daily_bars(y)
                    except Exception:
                        pass
                cycle(True, True)
                STATE["daily"] = load_daily(list(STATE["meta"]), log)
            live = M.is_open()
            slow = time.time() < STATE["slow_until"]
            every = 12 if live and not slow else 60 if live else 300
            if time.time() - last["stocks"] >= every:
                st = time.time() - last["struct"] >= 60
                cycle(True, st)
                last["stocks"] = time.time()
                if st:
                    last["struct"] = time.time()
            elif live and not slow:
                cycle(False, False)
        except Exception as e:
            log(f"us feed: {e}")
        time.sleep(4 if M.is_open() else 60)
