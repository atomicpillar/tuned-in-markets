"""Your watchlist: the stocks you are following, with your own note and an optional price level, kept in `data/watchlist.json`
on this computer. The view joins each stock with its live price, its screener score, where its P/E sits against its own history and
its next earnings date. A background check raises an alert (the bell in the top bar) when a stock reaches your price, when
earnings are within three days, or when it moves 5% or more in a day."""
import json
import threading
import time
from datetime import date, datetime

from sm import feed as IN
from us import market as M

FILE = M.DATA / "watchlist.json"
LOCK = threading.Lock()
FIRED = {}
SNAP = {"US": {"t": 0, "v": {}}, "IN": {"t": 0, "v": {}}}


def _load():
    try:
        return json.loads(FILE.read_text())
    except Exception:
        return {"US": {}, "IN": {}}


def _save(d):
    FILE.write_text(json.dumps(d, indent=1))


def norm(mk, sym):
    sym = sym.strip().upper()
    return sym.replace(".", "-") if mk == "US" else sym


def add(mk, sym, note="", target=None, price=None):
    sym = norm(mk, sym)
    with LOCK:
        d = _load()
        d.setdefault(mk, {})
        if sym not in d[mk]:
            d[mk][sym] = {"added": date.today().isoformat(), "added_price": price, "note": note or "", "target": target}
        else:
            d[mk][sym].update(note=note or d[mk][sym].get("note", ""), target=target if target is not None else d[mk][sym].get("target"))
        _save(d)
    return d[mk][sym]


def update(mk, sym, note=None, target="__keep__"):
    sym = norm(mk, sym)
    with LOCK:
        d = _load()
        e = d.get(mk, {}).get(sym)
        if e is None:
            return None
        if note is not None:
            e["note"] = note
        if target != "__keep__":
            e["target"] = target
            FIRED.pop((mk, sym, "target"), None)
        _save(d)
        return e


def remove(mk, sym):
    sym = norm(mk, sym)
    with LOCK:
        d = _load()
        d.get(mk, {}).pop(sym, None)
        _save(d)


def symbols(mk):
    return list(_load().get(mk, {}))


def quotes(mk, syms):
    """Live prices for the watched symbols (Yahoo's batch feed, cached 15 seconds)."""
    s = SNAP[mk]
    if time.time() - s["t"] < 15 and all(x in s["v"] for x in syms):
        return s["v"]
    ys = [x + ".NS" if mk == "IN" else x for x in syms]
    got = {}
    try:
        for i in range(0, len(ys), 20):
            got.update(IN.spark(ys[i:i + 20]))
    except Exception:
        pass
    out = {}
    for x, y in zip(syms, ys):
        g = got.get(y)
        if g and g.get("ltp"):
            out[x] = {"ltp": round(g["ltp"], 2), "pct": round((g["ltp"] / g["prev"] - 1) * 100, 2) if g.get("prev") else None}
    SNAP[mk] = {"t": time.time(), "v": out}
    return out


def _name(mk, sym):
    try:
        if mk == "US":
            from us import universe as U
            return (U.U["list"].get(sym) or U.U["all"].get(sym) or {}).get("name") or sym
        from sx import universe as IU
        return (IU.U["list"].get(sym) or {}).get("name") or (IU.U["cls"].get(sym) or {}).get("name") or sym
    except Exception:
        return sym


def _cached_detail(mk, sym):
    p = M.DATA / "lt" / f"{mk}-{sym}.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def view(mk):
    from . import screen
    from . import stock
    d = _load().get(mk, {})
    syms = list(d)
    q = quotes(mk, syms) if syms else {}
    table = {r["sym"]: r for r in ((screen.load(mk) or {}).get("rows") or [])}
    rows = []
    for s in syms:
        e, p = d[s], q.get(s) or {}
        det = _cached_detail(mk, s)
        if det is None:                      # build the long-term detail in the background so the next refresh has valuation and earnings
            threading.Thread(target=lambda a=s: stock.detail(mk, a), daemon=True).start()
        pe = (det or {}).get("pe_stats") or {}
        ev = (det or {}).get("events") or {}
        t = table.get(s) or {}
        ltp = p.get("ltp")
        rows.append({"sym": s, "name": _name(mk, s), "ltp": ltp, "pct": p.get("pct"), "note": e.get("note", ""), "added": e.get("added"), "added_price": e.get("added_price"),
                     "since": round((ltp / e["added_price"] - 1) * 100, 1) if ltp and e.get("added_price") else None, "target": e.get("target"),
                     "to_target": round((e["target"] / ltp - 1) * 100, 1) if ltp and e.get("target") else None,
                     "score": t.get("score"), "s_quality": t.get("s_quality"), "s_growth": t.get("s_growth"), "s_value": t.get("s_value"),
                     "pe_now": pe.get("now"), "pe_median": pe.get("median"), "pe_pctile": pe.get("pctile"), "next_earnings": ev.get("next_earnings"),
                     "high52": ((det or {}).get("price") or {}).get("high52"), "low52": ((det or {}).get("price") or {}).get("low52")})
    return {"mkt": mk, "rows": rows}


def _check(mk, emit):
    d = _load().get(mk, {})
    if not d:
        return
    import alerts
    live = alerts._open(mk)                  # price levels and big moves count only while the market is trading
    q = quotes(mk, list(d))
    today = date.today().isoformat()
    for s, e in d.items():
        p = q.get(s)
        if not p:
            continue
        ltp, pct, t = p["ltp"], p["pct"], e.get("target")
        if live and t and (mk, s, "target") not in FIRED and e.get("added_price"):
            hit = ltp <= t if t < e["added_price"] else ltp >= t
            if hit:
                FIRED[(mk, s, "target")] = 1
                emit(mk, s, "WATCH", f"Reached your price level of {t}: now {ltp}.", "bull" if ltp >= t else "bear", ltp, pct)
        if live and pct is not None and abs(pct) >= 5 and FIRED.get((mk, s, "move")) != today:
            FIRED[(mk, s, "move")] = today
            emit(mk, s, "WATCH", f"Moved {pct:+.1f}% today, more than the 5% you asked to be told about.", "bull" if pct > 0 else "bear", ltp, pct)
        det = _cached_detail(mk, s)
        ne = ((det or {}).get("events") or {}).get("next_earnings")
        if ne and FIRED.get((mk, s, "earn")) != ne:
            days = (datetime.strptime(ne, "%Y-%m-%d").date() - date.today()).days
            if 0 <= days <= 3:
                FIRED[(mk, s, "earn")] = ne
                emit(mk, s, "WATCH", f"Reports earnings on {ne} ({'today' if days == 0 else f'in {days} day' + ('s' if days > 1 else '')}).", "bull", ltp, pct)


def run(log=print):
    import alerts
    while True:
        for mk in ("US", "IN"):
            try:
                _check(mk, alerts._emit)
            except Exception as e:
                log(f"watchlist {mk}: {e}")
        time.sleep(60)
