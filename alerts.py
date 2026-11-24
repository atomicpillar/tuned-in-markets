"""Alerts: what changed on the tape since the last look, for both markets.

Every 15 seconds the live tape (every F&O stock in India, every S&P 500 and Nasdaq-100 stock in the US) is compared
with the previous look. An alert is something that newly happened:
  STRUCTURE  a stock's latest 5-minute structure break is new (BOS = trend continues, CHoCH = first sign of a turn)
  SWEEP      price took out the previous day's high (PDH) or low (PDL) for the first time today
  DISPLACE   the move since the open passed twice a normal day's range for that stock
  INDEX      an index card's structure changed
The first look after a start only records the state, so a restart never floods the list. Alerts are rules on
public prices, not advice."""
import json
import threading
import time
from collections import deque

from sm import feed as IN
from sm import market as SM
from us import feed as UF
from us import market as USM

LOG = {"IN": deque(maxlen=400), "US": deque(maxlen=400)}
SEEN = {"IN": {}, "US": {}}
LOCK = threading.Lock()
SEQ = {"n": 0}


def _tape(mk):
    return (IN.STATE if mk == "IN" else UF.STATE)


def _open(mk):
    return SM.is_open() if mk == "IN" else USM.is_open()


def _emit(mk, sym, kind, text, direction, ltp, pct):
    with LOCK:
        SEQ["n"] += 1
        LOG[mk].appendleft({"id": SEQ["n"], "t": int(time.time()), "mkt": mk, "sym": sym, "kind": kind, "dir": direction, "text": text, "ltp": ltp, "pct": pct})


def look(mk):
    st = _tape(mk)
    seen, first = SEEN[mk], not SEEN[mk].get("_ready")
    day = (SM.now_ist() if mk == "IN" else USM.now_et()).date().isoformat()
    if seen.get("_day") != day:
        seen.clear()
        seen["_day"] = day
        first = True
    live = _open(mk)
    rows = [(r["sym"], r) for r in list(st["stocks"].values())] + [(k, {**v, "sym": k, "indexcard": True}) for k, v in st["indices"].items()]
    for sym, r in rows:
        # nothing fires on the first look at a symbol, on the first look after a start, or while the market is shut:
        # those looks only record where things stand, so late-arriving data never looks like an event
        quiet = first or not live or ("seen", sym) not in seen
        seen[("seen", sym)] = 1
        rd = r.get("read") or {}
        s = rd.get("struct")
        if s:
            sig = f"{s['type']}|{s['dir']}|{s['time']}"
            if seen.get(("st", sym)) != sig:
                if not quiet and seen.get(("st", sym)) is not None:
                    up = s["dir"] == "bull"
                    what = "Change of character: first sign the move is turning" if s["type"] == "CHoCH" else "Break of structure: the trend is continuing"
                    _emit(mk, sym, "INDEX" if r.get("indexcard") else "STRUCTURE", f"{s['type']} {'up' if up else 'down'} on the 5-minute chart at {s['time']}. {what}.", s["dir"], r.get("ltp"), r.get("pct"))
                seen[("st", sym)] = sig
        if "pdh" in r:                                    # yesterday's levels are loaded, so a sweep is a real reading
            fresh = ("lv", sym) not in seen
            seen[("lv", sym)] = 1
            for k in r.get("liq") or []:
                if ("sw", sym, k) not in seen:
                    seen[("sw", sym, k)] = 1
                    if not quiet and not fresh:
                        _emit(mk, sym, "SWEEP", f"Took out the previous day's {'high' if k == 'PDH' else 'low'} ({k}). Price went past the level where stops sit.", "bull" if k == "PDH" else "bear", r.get("ltp"), r.get("pct"))
        d = r.get("disp")
        if d is not None and abs(d) >= 2 and ("dp", sym) not in seen:
            seen[("dp", sym)] = 1
            if not quiet:
                _emit(mk, sym, "DISPLACE", f"Moved {abs(d):.1f}× a normal day's range since the open ({r.get('from_open'):+.2f}%).", "bull" if d > 0 else "bear", r.get("ltp"), r.get("pct"))
    seen["_ready"] = True


def run(log=print):
    while True:
        for mk in ("IN", "US"):
            try:
                if _tape(mk)["stocks"]:
                    look(mk)
            except Exception as e:
                log(f"alerts {mk}: {e}")
        time.sleep(15)


def view(mk, since=0):
    with LOCK:
        items = [a for a in LOG[mk] if a["id"] > since]
    return {"alerts": items[:60], "last": SEQ["n"], "open": _open(mk)}
