"""Market-wide scan: every listed stock and ETF, not just the indexes.

India: all NSE-listed equities (EQUITY_L.csv, about 2,600) and ETFs (about 360). US: every Nasdaq / NYSE /
NYSE American / Arca / Cboe listing from Nasdaq's directory (about 5,600 stocks and 5,700 ETFs).
Prices come from Yahoo's batch feed, 20 symbols a call, four polite workers; one full sweep takes a few
minutes and repeats while the market is open. The page shows breadth (how many rose and fell), the biggest
movers, and lets any symbol open its chart."""
import csv
import io
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from sm import feed as IN
from sm import market as SM
from us import feed as UF
from us import market as USM
from us import universe as UU

STATE = {"IN": {"rows": {}, "time": None, "sweeping": False, "total": 0}, "US": {"rows": {}, "time": None, "sweeping": False, "total": 0}}
LISTS = {"IN": {}, "US": {}}
MIN_PRICE = {"IN": 10, "US": 1}
LOCK = threading.Lock()


def india_list():
    out = {}
    rows = csv.DictReader(io.StringIO(SM.get("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv").decode()))
    for r in rows:
        s = (r.get("SYMBOL") or "").strip()
        if s:
            out[s] = {"name": (r.get("NAME OF COMPANY") or s).title(), "etf": False, "ex": (r.get(" SERIES") or "").strip(), "y": s + ".NS"}
    try:
        for r in csv.DictReader(io.StringIO(SM.get("https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv").decode())):
            s = (r.get("Symbol") or "").strip()
            if s:
                out.setdefault(s, {"name": (r.get("SecurityName") or s).title(), "etf": True, "ex": "ETF", "y": s + ".NS"})
    except Exception:
        pass
    return out


def us_list():
    UU.load_lists()
    return {s: {"name": v["name"], "etf": bool(v.get("etf")) or " ETN" in v["name"] or "ETNs" in v["name"] or " due 20" in v["name"], "ex": v.get("ex", ""), "y": s}
            for s, v in UU.U["all"].items() if "acquisition corp" not in v["name"].lower()}


def lists(mk):
    if not LISTS[mk]:
        LISTS[mk] = india_list() if mk == "IN" else us_list()
        STATE[mk]["total"] = len(LISTS[mk])
    return LISTS[mk]


def sweep(mk, log=print):
    st = STATE[mk]
    if st["sweeping"]:
        return
    st["sweeping"] = True
    try:
        lst = lists(mk)
        ys = [v["y"] for v in lst.values()]
        by_y = {v["y"]: s for s, v in lst.items()}
        chunks = [ys[i:i + 20] for i in range(0, len(ys), 20)]
        rows, slow = {}, {"until": 0}

        def one(chunk):
            for attempt in range(2):
                if slow["until"] > time.time():
                    time.sleep(slow["until"] - time.time())
                try:
                    got = IN.spark(chunk)
                    for y, g in got.items():
                        if g["ltp"] and g["prev"]:
                            s = by_y.get(y)
                            if s:
                                rows[s] = {"sym": s, "name": lst[s]["name"], "etf": lst[s]["etf"], "ex": lst[s]["ex"], "ltp": round(g["ltp"], 2),
                                           "pct": round((g["ltp"] / g["prev"] - 1) * 100, 2), "t": g.get("time")}
                    return
                except Exception as e:
                    if "429" in str(e):
                        slow["until"] = time.time() + 60
                        continue
                    return
            time.sleep(0.05)

        with ThreadPoolExecutor(4) as ex:
            list(ex.map(one, chunks))
        with LOCK:
            st["rows"].update(rows)
            st["time"] = time.time()
        log(f"scan {mk}: {len(rows)} of {len(ys)} priced")
    except Exception as e:
        log(f"scan {mk}: {e}")
    finally:
        st["sweeping"] = False


def run(log=print):
    last = {"IN": 0, "US": 0}
    for _ in range(60):                                # the live tapes come first: the scan starts once either has prices (at most 5 minutes)
        if IN.STATE["stocks"] or UF.STATE["stocks"]:
            break
        time.sleep(5)
    time.sleep(30)
    while True:
        for mk, is_open in (("US", USM.is_open()), ("IN", SM.is_open())):
            every = 300 if is_open else 3600
            if time.time() - last[mk] >= every:
                last[mk] = time.time()
                sweep(mk, log)
        time.sleep(20)


def price(mk, sym):
    return STATE[mk]["rows"].get(sym)


def view(mk, kind="stocks", minp=None, limit=25, q=""):
    st = STATE[mk]
    minp = MIN_PRICE[mk] if minp is None else minp
    with LOCK:
        rows = list(st["rows"].values())
    if kind == "stocks":
        rows = [r for r in rows if not r["etf"]]
    elif kind == "etf":
        rows = [r for r in rows if r["etf"]]
    q = q.strip().upper()
    if q:
        hits = [r for r in rows if q == r["sym"] or q in r["sym"] or q in r["name"].upper()]
        hits.sort(key=lambda r: (r["sym"] != q, not r["sym"].startswith(q), len(r["sym"])))
        return {"hits": hits[:20], "count": len(rows)}
    pr = [r for r in rows if r["ltp"] >= minp]
    adv, dec = sum(r["pct"] > 0 for r in pr), sum(r["pct"] < 0 for r in pr)
    flat = len(pr) - adv - dec
    big = lambda s: sum(1 for r in pr if (r["pct"] >= 5 if s > 0 else r["pct"] <= -5))
    return {"time": st["time"], "sweeping": st["sweeping"], "total": st["total"], "priced": len(rows), "shown": len(pr), "min_price": minp, "kind": kind,
            "breadth": {"adv": adv, "dec": dec, "flat": flat, "up5": big(1), "down5": big(-1)},
            "up": sorted(pr, key=lambda r: -r["pct"])[:limit], "down": sorted(pr, key=lambda r: r["pct"])[:limit]}
