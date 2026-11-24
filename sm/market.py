"""NSE clock in IST (hours, holidays) and plain HTTP helpers shared by the app."""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
UA = {"User-Agent": "Mozilla/5.0"}
DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
HOLI = DATA / "holidays.json"


_YAHOO = threading.BoundedSemaphore(4)       # background jobs: never more than 4 Yahoo requests in flight, Yahoo throttles bursts
_YAHOO_UI = threading.BoundedSemaphore(4)    # requests a person is waiting on (opening a chart) have their own lane so background loading cannot starve them
_YAHOO_LIVE = threading.BoundedSemaphore(3)  # the live tape (spark) has a lane of its own: bulk downloads must never freeze the clock and the prices
LANE = threading.local()


CALLS = {}                                   # host -> recent request times, for the health view
BLOCKED = {"429": 0}


def _count(url):
    import collections
    host = url.split("/")[2] if "//" in url else url
    dq = CALLS.setdefault(host, collections.deque(maxlen=2000))
    dq.append(time.time())


def stats():
    now = time.time()
    return {"per_min": {h: sum(1 for t in dq if now - t < 60) for h, dq in CALLS.items()}, "rate_limited": BLOCKED["429"]}


def get(url, timeout=20):
    _count(url)
    req = urllib.request.Request(url, headers=UA)
    if "yahoo" in url:
        with (_YAHOO_LIVE if "/spark" in url else _YAHOO_UI if getattr(LANE, "ui", False) else _YAHOO):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    BLOCKED["429"] += 1
                raise
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url, timeout=20):
    return json.loads(get(url, timeout))


def holidays():
    """NSE trading holidays from NSE's public list, refreshed once a week."""
    try:
        d = json.loads(HOLI.read_text())
        if time.time() - d["fetched"] < 7 * 86400:
            return set(d["days"])
    except Exception:
        d = None
    try:
        rows = get_json("https://www.nseindia.com/api/holiday-master?type=trading", 15).get("CM", [])
        days = sorted({datetime.strptime(r["tradingDate"], "%d-%b-%Y").date().isoformat() for r in rows})
        HOLI.write_text(json.dumps({"days": days, "fetched": time.time()}))
        return set(days)
    except Exception:
        return set(d["days"]) if d else set()


def now_ist():
    return datetime.now(IST)


def is_trading_day(d, hol=None):
    return d.weekday() < 5 and d.isoformat() not in (hol if hol is not None else holidays())


def market_status(t=None):
    t = t or now_ist()
    m = t.hour * 60 + t.minute
    if not is_trading_day(t.date()):
        return "closed"
    if m < 555:
        return "pre-open" if m >= 540 else "closed"
    return "open" if m < 930 else "closed"


def is_open():
    return market_status() == "open"


def session_minutes(idx):
    """Minutes since 09:15 IST for a UTC index, and each bar's IST date."""
    lt = idx.tz_convert(IST)
    return (lt.hour - 9) * 60 + lt.minute - 15, pd.Index(lt.date)


def minute_now():
    t = now_ist()
    return t.hour * 60 + t.minute - 555
