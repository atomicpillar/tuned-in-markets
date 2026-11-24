"""Market breadth: how healthy the market is underneath the index.

For the S&P 1500 (US) or the Nifty 500 (India): the share of stocks above their 200-day and 50-day averages, how many are at a
52-week high or low, how many rose and fell today, and the market's fear gauge (VIX, or India VIX). Each close the day's reading is
saved, so the page can draw the advance-decline line and the trend of the 200-day share over time. All of it comes from the daily bars
and live prices the dashboard already holds; nothing is estimated."""
import json
import threading
import time
from datetime import timedelta

import pandas as pd

from sm import feed as IN
from sm import market as SM
from us import market as USM

CACHE = {"US": {"t": 0, "v": None}, "IN": {"t": 0, "v": None}}
LOCK = threading.Lock()
VIX = {"US": "^VIX", "IN": "^INDIAVIX"}


def _universe(mk):
    if mk == "US":
        from us import sector as SC
        from us import universe as U
        return U.U["hist"], list(U.U["list"]), (lambda s: SC.price(s)), "IDX:^GSPC"
    from sx import live as L
    from sx import universe as IU
    return IU.U["hist"], list(IU.U["list"]), (lambda s: L.price(s)), "IDX:NIFTY 50"


def _open(mk):
    return USM.is_open() if mk == "US" else SM.is_open()


def last_session(mk):
    if mk == "US":
        return USM.last_session().isoformat()
    d = SM.now_ist().date()
    hol = SM.holidays()
    while not SM.is_trading_day(d, hol):
        d -= timedelta(days=1)
    return d.isoformat()


def _file(mk):
    return SM.DATA / f"breadth_{mk}.json"


def history(mk):
    try:
        return json.loads(_file(mk).read_text())
    except Exception:
        return {}


def compute(mk):
    hist, syms, price, bench = _universe(mk)
    n = a200 = a50 = n200 = n50 = nh = nl = near = adv = dec = flat = 0
    for s in syms:
        h = hist.get(s)
        if h is None or len(h) < 55:
            continue
        c = h["close"]
        p = price(s) or {}
        ltp = p.get("ltp") or float(c.iloc[-1])
        n += 1
        if len(c) >= 200:
            n200 += 1
            a200 += ltp > float(c.iloc[-200:].mean())
        n50 += 1
        a50 += ltp > float(c.iloc[-50:].mean())
        hi, lo = float(h["high"].iloc[-252:].max()), float((h["low"] if "low" in h else c).iloc[-252:].min())
        nh += ltp >= hi
        nl += ltp <= lo
        near += ltp >= hi * .98
        pc = p.get("pct")
        if pc is not None:
            adv += pc > 0
            dec += pc < 0
            flat += pc == 0
    vix = None
    try:
        g = IN.spark([VIX[mk]]).get(VIX[mk])
        if g and g.get("ltp"):
            vix = {"last": round(g["ltp"], 2), "pct": round((g["ltp"] / g["prev"] - 1) * 100, 2) if g.get("prev") else None}
    except Exception:
        pass
    return {"n": n, "above200": round(a200 / n200 * 100, 1) if n200 else None, "above50": round(a50 / n50 * 100, 1) if n50 else None, "n200": n200,
            "new_highs": int(nh), "new_lows": int(nl), "near_high": int(near), "adv": int(adv), "dec": int(dec), "flat": int(flat), "vix": vix,
            "universe": "S&P 1500" if mk == "US" else "Nifty 500", "session": last_session(mk), "open": _open(mk)}


def record(mk, v):
    """Save the close's reading once per session (only when the market is shut and the figures are complete)."""
    if v["open"] or not v["n"] or v["above200"] is None:
        return
    h = history(mk)
    if v["session"] in h:
        return
    h[v["session"]] = {k: v[k] for k in ("above200", "above50", "new_highs", "new_lows", "adv", "dec")}
    _file(mk).write_text(json.dumps(dict(sorted(h.items())[-400:])))


def view(mk):
    c = CACHE[mk]
    if c["v"] is None or time.time() - c["t"] > ((45 if _open(mk) else 600) if c["v"]["n"] else 5):      # an empty reading (history not loaded yet) is never kept
        with LOCK:
            v = compute(mk)
            try:
                record(mk, v)
            except Exception:
                pass
            c["v"], c["t"] = v, time.time()
    v = dict(c["v"])
    h = history(mk)
    days = sorted(h)
    ad, acc = [], 0
    for d in days:
        acc += h[d]["adv"] - h[d]["dec"]
        ad.append([d, acc])
    v["history"] = {"days": days, "above200": [h[d]["above200"] for d in days], "above50": [h[d]["above50"] for d in days], "ad_line": ad,
                    "new_highs": [h[d]["new_highs"] for d in days], "new_lows": [h[d]["new_lows"] for d in days]}
    return v
