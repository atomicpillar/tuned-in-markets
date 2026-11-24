"""NYSE / Nasdaq clock in New York time (hours, holidays) and the plain HTTP helpers the US engine shares.
Holidays are computed from the exchange's published rules, so there is nothing to download."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from sm.market import DATA, UA, get, get_json  # noqa: F401  (shared helpers)

ET = ZoneInfo("America/New_York")
OPEN_MIN, SESSION_MIN = 570, 390            # 09:30 ET, and 390 minutes to the 16:00 close


def _nth(y, month, weekday, n):
    d = date(y, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(days=7 * (n - 1))


def _last(y, month, weekday):
    d = date(y + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo, da = divmod(h + l - 7 * m + 114, 31)
    return date(y, mo, da + 1)


def _observed(d):
    """A holiday on Saturday is taken on Friday, on Sunday on Monday."""
    return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d


_HOL = {}


def holidays(y=None):
    y = y or now_et().year
    if y in _HOL:
        return _HOL[y]
    days = set()
    for yy in (y, y + 1):
        ny = date(yy, 1, 1)
        if ny.weekday() != 5:                                  # a Saturday New Year is not moved to Friday
            days.add(_observed(ny))
    days |= {_nth(y, 1, 0, 3), _nth(y, 2, 0, 3), _easter(y) - timedelta(days=2), _last(y, 5, 0),
             _observed(date(y, 6, 19)), _observed(date(y, 7, 4)), _nth(y, 9, 0, 1), _nth(y, 11, 3, 4), _observed(date(y, 12, 25))}
    _HOL[y] = {d.isoformat() for d in days}
    return _HOL[y]


def now_et():
    return datetime.now(ET)


def is_trading_day(d):
    return d.weekday() < 5 and d.isoformat() not in holidays(d.year)


def close_min(d):
    """Early 13:00 closes: the day after Thanksgiving, Christmas Eve and July 3 when they are trading days."""
    if d == _nth(d.year, 11, 3, 4) + timedelta(days=1) or (d.month, d.day) in ((12, 24), (7, 3)) and d.weekday() < 5:
        return 780
    return 960


def market_status(t=None):
    t = t or now_et()
    if not is_trading_day(t.date()):
        return "closed"
    m = t.hour * 60 + t.minute
    if 240 <= m < OPEN_MIN:
        return "pre-open"
    return "open" if OPEN_MIN <= m < close_min(t.date()) else "closed"


def is_open():
    return market_status() == "open"


def minute_now():
    t = now_et()
    return t.hour * 60 + t.minute - OPEN_MIN


def session_minutes(idx):
    """Minutes since 09:30 ET for a UTC index, and each bar's New York date."""
    lt = idx.tz_convert(ET)
    return (lt.hour - 9) * 60 + lt.minute - 30, pd.Index(lt.date)


def last_session(d=None):
    d = d or now_et().date()
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d
