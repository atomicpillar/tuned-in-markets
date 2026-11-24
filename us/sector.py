"""The US Sector Map: live state and the views the page asks for. Same JSON shapes as the India sector map
(horizon, sector, stock, search, chart, tick), built on US data.

Live state:
- the 20 sector ETFs, the three indices and SPY on Yahoo's batch feed every 5 s (a few seconds behind)
- every S&P 1500 stock on the same feed every 60 s (every 10 min when the market is closed)
- whatever sector or stock is open on the page: its stocks every 5 s
- market value, P/E, 52-week range and volume per stock from Yahoo's batch quote once an hour (needs Yahoo's crumb)
Every 5 minutes the sectors' moves are recorded so the day can be replayed and each bubble can show a trail."""
import json
import threading
import time
import urllib.parse
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import feed as FD
from . import market as M
from . import news as N
from . import universe as U
from . import yahoo as Y
from sm import feed as IN
from sm import smc

DAYS = M.DATA / "us_days"
DAYS.mkdir(exist_ok=True)
S = {"quotes": {}, "spark": {}, "focus": [], "focus_until": 0, "day": {"snaps": []}, "time": None, "errors": 0, "slow_until": 0, "qtime": 0}
LOCK = threading.Lock()
_C = {}
BENCH = "^GSPC"
NAME = "S&P 500"


def cached(key, secs, fn):
    if key in _C and time.time() - _C[key][0] < secs:
        return _C[key][1]
    v = fn()
    _C[key] = (time.time(), v)
    return v


def r2(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 2)


def spark(symbols):
    got, slow = {}, False
    for i in range(0, len(symbols), 20):
        try:
            got.update(IN.spark(symbols[i:i + 20]))
        except Exception as e:
            S["errors"] += 1
            if "429" in str(e):
                S["slow_until"] = time.time() + 120
                slow = True
                break
        time.sleep(0.08)
    return got, slow


def focus(syms):
    S["focus"] = [s for s in syms if s in U.U["list"]][:120]
    S["focus_until"] = time.time() + 60


def price(sym):
    """Best live price: the batch feed when it is fresh, else the last hourly quote."""
    q = S["quotes"].get(sym) or {}
    y = S["spark"].get(sym)
    base = {"sym": sym, "ltp": q.get("regularMarketPrice"), "pct": q.get("regularMarketChangePercent"), "prev": q.get("regularMarketPreviousClose"),
            "volume": q.get("regularMarketVolume"), "ffmc": q.get("marketCap") or 0, "name": q.get("longName") or q.get("shortName")}
    if y and y["ltp"]:
        prev = y["prev"] or base["prev"]
        return {**base, "ltp": y["ltp"], "pct": round((y["ltp"] / prev - 1) * 100, 2) if prev else base["pct"], "live": M.is_open()}
    if not base["ltp"]:
        import scan
        sp = scan.price("US", sym)               # a stock outside the S&P 1500: the market-wide scan has its price
        if sp:
            return {**base, "ltp": sp["ltp"], "pct": sp["pct"]}
    return base


def index_value(name):
    """A sector ETF's or index's level and move: live from the feed, week and month from its daily history."""
    y = name
    g = S["spark"].get(y)
    h = U.U["hist"].get("IDX:" + y)
    ix = {}
    if g and g["ltp"] and g["prev"]:
        ix.update(last=round(g["ltp"], 2), pct=round((g["ltp"] / g["prev"] - 1) * 100, 2), live=M.is_open())
    if h is not None and len(h) > 25:
        c = h["close"]
        ix["w1"], ix["m1"] = r2(ret(c, 5)), r2(ret(c, 21))
        ix.setdefault("last", r2(c.iloc[-1]))
        if "pct" not in ix:
            ix["pct"] = r2((c.iloc[-1] / c.iloc[-2] - 1) * 100)
    q = S["quotes"].get(y) or {}
    if q.get("trailingPE"):
        ix["pe"] = r2(q["trailingPE"])
    return ix


def ret(series, n):
    if series is None or len(series) <= n:
        return None
    return float(series.iloc[-1] / series.iloc[-1 - n] - 1) * 100


def record():
    m = M.minute_now()
    if not (0 <= m <= M.SESSION_MIN):
        return
    d = S["day"]
    if d["snaps"] and d["snaps"][-1]["m"] > m - 5:
        return
    snap = {"m": m, "nifty": index_value(BENCH).get("pct"), "sec": {}}
    for sec in U.SECTORS:
        v = index_value(sec["index"]).get("pct")
        if v is not None:
            snap["sec"][sec["name"]] = v
    d["snaps"].append(snap)
    (DAYS / f"{M.now_et().date()}.json").write_text(json.dumps(d))


def load_quotes(log=print):
    """Market value, P/E, 52-week range and volume for the whole S&P 1500 and the ETFs; Yahoo's batch quote."""
    ys = list(U.U["list"]) + [s["index"] for s in U.SECTORS] + list(U.INDICES.values())
    try:
        q = Y.quotes(ys)
    except Exception as e:
        log(f"US quotes: {e}")
        return
    with LOCK:
        S["quotes"].update(q)
        S["qtime"] = time.time()
    for s, v in U.U["list"].items():
        r = q.get(s)
        if r:
            c = U.U["cls"].setdefault(s, {})
            c.update(name=v["name"], sector=v["sector"], industry=v["sub"], basic=v["sub"], mcap=r.get("marketCap"), pe=r.get("trailingPE"),
                     high52=r.get("fiftyTwoWeekHigh"), low52=r.get("fiftyTwoWeekLow"), volume=r.get("regularMarketVolume"))
    log(f"US quotes: {len(q)} symbols")


def classify():
    """Sector and sub-industry for every stock are known from the lists even before the quotes arrive."""
    for s, v in U.U["list"].items():
        c = U.U["cls"].setdefault(s, {})
        c.setdefault("name", v["name"])
        c.update(sector=v["sector"], industry=v["sub"], basic=v["sub"])


def run(log=print):
    last = {"day": None, "fast": 0, "all": 0, "quotes": 0}
    while True:
        try:
            today = M.now_et().date()
            if last["day"] != today:
                p = DAYS / f"{today}.json"
                S["day"] = json.loads(p.read_text()) if p.exists() else {"snaps": []}
                last["day"] = today
            live = M.is_open()
            if time.time() - last["quotes"] >= 3600:
                load_quotes(log)
                last["quotes"] = time.time()
            if time.time() > S["slow_until"]:
                if time.time() - last["fast"] >= (5 if live else 120):
                    ys = list(dict.fromkeys([BENCH] + list(U.INDICES.values()) + [s["index"] for s in U.SECTORS]))
                    if time.time() < S["focus_until"]:
                        ys += S["focus"]
                    got, _ = spark(ys)
                    with LOCK:
                        S["spark"].update(got)
                    last["fast"] = time.time()
                if last["fast"] and time.time() - last["all"] >= (60 if live else 900):      # after the ETFs are in
                    got, _ = spark(list(U.U["list"]))
                    with LOCK:
                        S["spark"].update(got)
                    last["all"] = time.time()
            record()
            S["time"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        except Exception as e:
            log(f"us sector: {e}")
        time.sleep(5 if M.is_open() else 30)


# ---------- views ----------

def sec_members(sec):
    return U.members(sec)


def series_for(sec):
    h = U.U["hist"].get("IDX:" + sec["index"])
    if h is not None and len(h) > 70:
        return h["close"].iloc[-70:] / h["close"].iloc[-70] * 100
    return U.sector_series(sec_members(sec))


def all_series():
    return cached(("series", M.now_et().date().isoformat(), len(U.U["hist"])), 3600, lambda: {s["name"]: series_for(s) for s in U.SECTORS})


def bench_hist():
    h = U.U["hist"].get("IDX:" + BENCH)
    return h["close"] if h is not None else None


def sector_move(sec, rng):
    ix = index_value(sec["index"])
    if rng == "today":
        return ix.get("pct")
    if rng in ("w1", "m1") and ix.get(rng) is not None:
        return ix.get(rng)
    return ret(all_series().get(sec["name"]), {"w1": 5, "m1": 21, "m3": 63}[rng])


def bench_move(rng):
    ix = index_value(BENCH)
    if rng == "today":
        return ix.get("pct")
    if rng in ("w1", "m1") and ix.get(rng) is not None:
        return ix[rng]
    return ret(bench_hist(), {"w1": 5, "m1": 21, "m3": 63}[rng])


def ranks_now(rng):
    v = {s["name"]: sector_move(s, rng) for s in U.SECTORS}
    order = sorted([k for k in v if v[k] is not None], key=lambda k: -v[k])
    return {k: i + 1 for i, k in enumerate(order)}, v


def rank_history(name, weeks=10):
    ser = all_series()
    out = []
    for w in range(weeks, -1, -1):
        end = -1 - w * 5
        vals = {}
        for k, s in ser.items():
            if s is not None and len(s) > 22 - end:
                vals[k] = float(s.iloc[end] / s.iloc[end - 21] - 1)
        order = sorted(vals, key=lambda k: -vals[k])
        if name in order:
            out.append({"date": str(ser[name].index[end].date()), "rank": order.index(name) + 1})
    return out


def themes():
    """Sub-industries across the S&P 1500 with at least 5 stocks: their middle stock today and how many beat the S&P 500."""
    bench = index_value(BENCH).get("pct") or 0
    by = {}
    for s, c in U.U["cls"].items():
        p = price(s)
        if c.get("basic") and p.get("pct") is not None:
            by.setdefault(c["basic"], []).append((s, p["pct"], c.get("sector")))
    out = []
    for b, rows in by.items():
        if len(rows) < 5:
            continue
        mid = float(np.median([r[1] for r in rows]))
        out.append({"name": b, "parent": rows[0][2], "n": len(rows), "beat": sum(r[1] > bench for r in rows), "pct": round(mid, 2)})
    return sorted([t for t in out if t["pct"] > bench], key=lambda t: -t["pct"])[:8]


def _day(iso):
    return pd.Timestamp(iso).tz_convert(M.ET).tz_localize(None).normalize()


def since(sec_name, iso):
    s = all_series().get(sec_name)
    if s is None:
        return None
    before = s[s.index < _day(iso)]
    if not len(before):
        return None
    today = index_value(next(x["index"] for x in U.SECTORS if x["name"] == sec_name)).get("pct") or 0
    return round((float(s.iloc[-1] / before.iloc[-1]) * (1 + today / 100) - 1) * 100, 2)


def pins(items, dates):
    out = {}
    ds = [pd.Timestamp(d) for d in dates]
    for h in items:
        t = _day(h["time"])
        cand = [d for d in ds if d <= t]
        if cand:
            out.setdefault(str(cand[-1].date()), []).append({"tag": h["tag"][0], "title": h["title"], "source": h["source"], "link": h["link"]})
    return out


def rel_chart(a, b, items):
    if a is None or b is None:
        return None
    df = pd.concat([a, b], axis=1).ffill().dropna().iloc[-55:]
    if len(df) < 5:
        return None
    df = df / df.iloc[0] * 100
    dates = [str(d.date()) for d in df.index]
    return {"dates": dates, "a": [r2(x) for x in df.iloc[:, 0]], "b": [r2(x) for x in df.iloc[:, 1]], "pins": pins(items, dates)}


def horizon(rng):
    rk, vals = ranks_now(rng)
    snaps = S["day"]["snaps"]
    first = snaps[0]["sec"] if snaps else {}
    rk_open = {k: i + 1 for i, k in enumerate(sorted(first, key=lambda k: -first[k]))} if first else {}
    secs = []
    for sec in U.SECTORS:
        mem = sec_members(sec)
        size = sum((S["quotes"].get(s) or {}).get("marketCap") or 0 for s in mem) or len(mem)
        ix = index_value(sec["index"])
        trail = snaps[-7]["sec"].get(sec["name"]) if rng == "today" and len(snaps) > 6 else None
        secs.append({"name": sec["name"], "index": sec["index"], "group": sec["group"], "v": r2(vals.get(sec["name"])), "size": size, "n": len(mem),
                     "rank": rk.get(sec["name"]), "rank_open": rk_open.get(sec["name"]), "trail": r2(trail), "live": bool(ix.get("live")),
                     "path": [[s["m"], s["sec"].get(sec["name"])] for s in snaps] if rng == "today" else []})
    climb = [{"name": s["name"], "from": s["rank_open"], "to": s["rank"]} for s in secs if s["rank_open"] and s["rank"]]
    if rng != "today":
        prev = {}
        for sec in U.SECTORS:
            sr = all_series().get(sec["name"])
            n = {"w1": 5, "m1": 21, "m3": 63}[rng]
            if sr is not None and len(sr) > n + 6:
                prev[sec["name"]] = float(sr.iloc[-6] / sr.iloc[-6 - n] - 1)
        order = sorted(prev, key=lambda k: -prev[k])
        climb = [{"name": k, "from": order.index(k) + 1, "to": rk[k]} for k in order if k in rk]
    news = []
    for sec in U.SECTORS:
        for h in N.sector(sec["name"], wait=False)[:4]:
            news.append({**h, "sector": sec["name"]})
    news.sort(key=lambda h: h["time"], reverse=True)
    for h in news[:14]:
        h["since"] = since(h["sector"], h["time"])
    mk = _C.get("mk", (0, []))[1]
    n = bench_hist()
    chart = None
    if n is not None:
        c = n.iloc[-60:]
        dates = [str(d.date()) for d in c.index]
        chart = {"dates": dates, "a": [r2(x) for x in c], "pins": pins(mk + news, dates)}
    bi = index_value(BENCH)
    return {"range": rng, "nifty": {"v": r2(bench_move(rng)), "last": bi.get("last")}, "sectors": secs, "groups": U.GROUPS, "climb": climb,
            "themes": themes() if rng == "today" else [], "news": news[:14], "chart": chart, "snaps": [{"m": s["m"], "nifty": s["nifty"]} for s in snaps]}


def stats(s):
    return U.stats(s)


def stock_row(s, c=None):
    c = c or U.U["cls"].get(s, {})
    p = price(s)
    st = stats(s)
    ltp = p.get("ltp")
    vr = (p.get("volume") or 0) / st["vol60"] if st.get("vol60") and p.get("volume") else None
    return {"sym": s, "name": c.get("name") or p.get("name") or s, "group": c.get("industry") or "Other", "basic": c.get("basic"),
            "ltp": r2(ltp), "pct": r2(p.get("pct")), "mcap": c.get("mcap") or p.get("ffmc") or 0, "live": bool(p.get("live")),
            "w1": r2(st.get("w1")), "m1": r2(st.get("m1")), "m3": r2(st.get("m3")),
            "above50": (ltp > st["dma50"]) if ltp and st.get("dma50") else None,
            "near_high": bool(ltp and (c.get("high52") or st.get("high52")) and ltp >= (c.get("high52") or st["high52"]) * .95),
            "vol_ratio": r2(vr), "high52": r2(c.get("high52") or st.get("high52")), "dma50": r2(st.get("dma50"))}


def sector_view(name, rng):
    sec = next((x for x in U.SECTORS if x["name"].lower() == name.lower()), None)
    if not sec:
        return {"error": "unknown sector"}
    mem = sec_members(sec)
    focus(mem)
    rows = [r for r in (stock_row(s) for s in mem) if r["ltp"]]
    groups = {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    glist = [{"name": g, "n": len(v), "mid": r2(np.median([r["pct"] for r in v if r["pct"] is not None])) if any(r["pct"] is not None for r in v) else None,
              "above50": sum(bool(r["above50"]) for r in v), "stocks": sorted(v, key=lambda r: -(r["mcap"] or 0))} for g, v in groups.items()]
    glist.sort(key=lambda g: -sum(r["mcap"] or 0 for r in g["stocks"]))
    if len(glist) > 6:
        rest = [r for g in glist[5:] for r in g["stocks"]]
        glist = glist[:5] + [{"name": "Other index members", "n": len(rest), "mid": r2(np.median([r["pct"] for r in rest if r["pct"] is not None])),
                              "above50": sum(bool(r["above50"]) for r in rest), "stocks": rest}]
    ix = index_value(sec["index"])
    rk, vals = ranks_now("today")
    snaps = S["day"]["snaps"]
    first = snaps[0]["sec"] if snaps else {}
    rk_open = sorted(first, key=lambda k: -first[k]).index(sec["name"]) + 1 if sec["name"] in first else None
    others = []                       # stocks the ETF holds that the classification files under another sector
    ser = all_series().get(sec["name"])
    wk_above = 0
    for r in rows:
        h = U.U["hist"].get(r["sym"])
        if h is not None and len(h) > 56:
            wk_above += int(h["close"].iloc[-6] > h["close"].iloc[-56:-6].mean())
    news = N.sector(sec["name"])
    for h in news:
        h["since"] = since(sec["name"], h["time"])
    mid = r2(np.median([r["pct"] for r in rows if r["pct"] is not None])) if rows else None
    bi = index_value(BENCH)
    return {"name": sec["name"], "index": sec["index"], "group": sec["group"],
            "ix": {"last": ix.get("last"), "pct": ix.get("pct"), "w1": r2(sector_move(sec, "w1")), "m1": r2(sector_move(sec, "m1")),
                   "m3": r2(sector_move(sec, "m3")), "pe": ix.get("pe"), "live": bool(ix.get("live"))},
            "nifty": {"pct": r2(bench_move("today")), "w1": r2(bench_move("w1")), "m1": r2(bench_move("m1")), "m3": r2(bench_move("m3")), "pe": bi.get("pe")},
            "rank": rk.get(sec["name"]), "rank_open": rk_open, "n": len(rows), "middle": mid, "groups": glist, "others": others,
            "rank_hist": rank_history(sec["name"]),
            "inside": {"above50": sum(bool(r["above50"]) for r in rows), "above50_wk": wk_above, "rose_week": sum((r["w1"] or 0) > 0 for r in rows),
                       "near_high": sum(r["near_high"] for r in rows), "busy": sum((r["vol_ratio"] or 0) > 1.5 for r in rows), "n": len(rows)},
            "movers": sorted([r for r in rows if r["w1"] is not None], key=lambda r: -r["w1"])[:6],
            "laggards": sorted([r for r in rows if r["w1"] is not None], key=lambda r: r["w1"])[:4],
            "news": news[:10], "chart": rel_chart(ser, bench_hist(), news)}


def stock_view(sym):
    sym = sym.upper().replace(".", "-")
    c = U.U["cls"].get(sym) or {}
    row = stock_row(sym, c)
    sec = next((x for x in U.SECTORS if sym in sec_members(x)), None)
    peers = []
    if sec:
        peers = [p for p in (stock_row(s) for s in sec_members(sec)) if p["group"] == row["group"] and p["ltp"]]
    focus([sym] + [p["sym"] for p in peers])
    st = stats(sym)
    h = U.U["hist"].get(sym)
    sser = all_series().get(sec["name"]) if sec else None
    against = []
    if sec:
        sx = index_value(sec["index"])
        for k, lab in (("today", "Today"), ("w1", "Week"), ("m1", "1 month"), ("m3", "3 months")):
            a = row["pct"] if k == "today" else row[k]
            b = sx.get("pct") if k == "today" else sector_move(sec, k)
            against.append({"label": lab, "stock": r2(a), "sector": r2(b), "gap": r2(a - b) if a is not None and b is not None else None})
    rank = None
    if sec and row["w1"] is not None:
        ws = sorted([p for p in (stock_row(s) for s in sec_members(sec)) if p["w1"] is not None], key=lambda p: -p["w1"])
        rank = {"pos": next((i + 1 for i, p in enumerate(ws) if p["sym"] == sym), None), "of": len(ws)}
    lines = None
    if h is not None and len(h) > 63:
        a = h["close"].iloc[-63:]
        lines = {"stock": [r2(x / a.iloc[0] * 100) for x in a]}
        n = bench_hist()
        if n is not None:
            nn = n.reindex(a.index).ffill()
            lines["nifty"] = [r2(x / nn.iloc[0] * 100) for x in nn]
        if sser is not None:
            ss = sser.reindex(a.index).ffill().bfill()
            lines["sector"] = [r2(x / ss.iloc[0] * 100) for x in ss]
        lines["m3"] = {"stock": r2(ret(h["close"], 63)), "sector": r2(sector_move(sec, "m3")) if sec else None, "nifty": r2(bench_move("m3"))}
    news = N.stock(sym, c.get("name"))
    vol60 = st.get("vol60")
    q = S["quotes"].get(sym) or {}
    return {"sym": sym, "row": row, "cls": {k: c.get(k) for k in ("sector", "industry", "basic", "pe", "mcap", "delivery", "high52", "low52", "name")},
            "sector": sec and {"name": sec["name"], "index": sec["index"]}, "peers": sorted(peers, key=lambda p: -(p["pct"] or -99)),
            "against": against, "rank": rank, "lines": lines, "news": news,
            "volume": {"today": q.get("regularMarketVolume"), "normal": r2(vol60), "ratio": r2((q.get("regularMarketVolume") or 0) / vol60) if vol60 else None},
            "delivery": None, "dma50": r2(st.get("dma50")), "chart": rel_chart(h["close"] if h is not None else None, bench_hist(), news)}


def search(q):
    """The S&P 1500 and the sectors first, then every US-listed stock and ETF."""
    q = q.strip().upper()
    out = [{"type": "sector", "name": s["name"]} for s in U.SECTORS if q in s["name"].upper()]
    for s, c in U.U["cls"].items():
        if q == s or q in (c.get("name") or "").upper() or q in s:
            out.append({"type": "stock", "sym": s, "name": c.get("name"), "pct": price(s).get("pct")})
        if len(out) > 14:
            return out
    for s, c in U.U["all"].items():
        if s in U.U["cls"]:
            continue
        if q == s or (len(q) > 2 and q in c["name"].upper()):
            out.append({"type": "stock", "sym": s, "name": c["name"] + (" (ETF)" if c.get("etf") else ""), "pct": price(s).get("pct")})
        if len(out) > 14:
            break
    return out


def chart(sym, tf):
    sym = sym.upper().replace(".", "-")
    return FD.chart(sym, tf)


def tick(syms):
    out = {s: {"ltp": r2(price(s).get("ltp")), "pct": r2(price(s).get("pct"))} for s in syms}
    ix = {s["name"]: {"v": r2(index_value(s["index"]).get("pct")), "last": index_value(s["index"]).get("last")} for s in U.SECTORS}
    n = index_value(BENCH)
    return {"stocks": out, "sectors": ix, "nifty": {"v": r2(n.get("pct")), "last": n.get("last")}, "time": S["time"], "market": M.market_status()}


def status():
    import scan
    from . import feed as FD
    from . import lab as LB
    stage = U.U["progress"] or ("waiting for the first prices" if not S["spark"] else "")
    return {"ready": bool(S["spark"]) and bool(U.U["cls"]), "progress": stage, "time": S["time"], "classified": len(U.U["cls"]),
            "history": len(U.U["hist"]), "quotes": len(S["quotes"]), "tape": len(FD.STATE["stocks"]), "listed": len(U.U["all"]),
            "scan_priced": len(scan.STATE["US"]["rows"]), "lab": LB.STATE["phase"], "lab_msg": LB.STATE["msg"],
            "sec_ready": __import__("envfile").sec_ready(), "now": __import__("time").time()}
