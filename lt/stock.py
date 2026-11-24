"""The long-term view of one stock: ten years of fundamentals, ratios, valuation against its own history, a weekly price
history, dividends, earnings, ownership and insiders. US figures come from SEC filings, India's from Yahoo's statements
(about four years) and NSE; every block names its source and a missing number stays missing. Cached 12 hours per stock."""
import json
import time

import numpy as np
import pandas as pd

from us import market as M
from . import events as EV
from . import sec as SEC
from . import yf as YF

DIR = M.DATA / "lt"
DIR.mkdir(exist_ok=True)
CRORE = 1e7


def _cagr(a, b, years):
    if a is None or b is None or a <= 0 or b <= 0 or years <= 0:
        return None
    return round(((b / a) ** (1 / years) - 1) * 100, 1)


def _pct(a, b):
    return None if a is None or not b else round(a / b * 100, 1)


def ratios(annual, financial=False):
    """What the annual rows say, in plain ratios. Each is None when its inputs are missing; none is estimated."""
    if not annual:
        return {}
    a = annual[-1]
    r = {"roe": _pct(a.get("net"), a.get("equity")), "op_margin": _pct(a.get("opinc"), a.get("revenue")), "net_margin": _pct(a.get("net"), a.get("revenue")),
         "gross_margin": _pct(a.get("gross"), a.get("revenue")), "fcf_margin": None if financial else _pct(a.get("fcf"), a.get("revenue")),
         "debt_equity": None if financial else round(a["debt"] / a["equity"], 2) if a.get("debt") is not None and a.get("equity") and a["equity"] > 0 else None,
         "net_cash": None if financial else (a["cash"] - a["debt"]) if a.get("cash") is not None and a.get("debt") is not None else None,
         "payout": _pct(a.get("div"), a.get("net")) if a.get("div") else None, "years": len(annual)}

    def at(n):
        return annual[-1 - n] if len(annual) > n else None
    for key, name in (("revenue", "rev"), ("net", "net"), ("eps", "eps"), ("fcf", "fcf")):
        for n in (3, 5):
            old = at(n)
            r[f"{name}_cagr{n}"] = None if (financial and key == "fcf") or not old else _cagr(old.get(key), a.get(key), n)
    old = at(3)
    r["share_change3"] = round((a["shares"] / old["shares"] - 1) * 100, 1) if old and old.get("shares") and a.get("shares") else None
    r["profitable_years"] = sum(1 for x in annual if x.get("net") is not None and x["net"] > 0)
    nets = [x["net"] for x in annual if x.get("net") is not None]
    r["n_years_net"] = len(nets)
    return r


def _stats(series, now):
    s = pd.Series([v for v in series if v is not None and 0 < v < 200], dtype=float)
    if len(s) < 20 or now is None or not (0 < now < 200):
        return None
    return {"now": round(now, 1), "median": round(float(s.median()), 1), "low": round(float(s.min()), 1), "high": round(float(s.max()), 1),
            "p25": round(float(s.quantile(.25)), 1), "p75": round(float(s.quantile(.75)), 1), "pctile": round(float((s < now).mean() * 100)), "n": int(len(s))}


def valuation_us(df, splits, pit):
    """P/E and P/S every week for ten years, using only what was filed by that day (first-filed values) and the price as
    quoted on that day (Yahoo's split adjustment undone, because the filings it is divided by are not adjusted)."""
    if not pit:
        return None
    px = YF.unadjusted(df, splits)
    q = sorted(pit, key=lambda x: x["end"])
    dates, pe, ps = [], [], []
    for d, price in px.items():
        day = d.strftime("%Y-%m-%d")
        known = [x for x in q if x["filed"] <= day]
        last4 = known[-4:]
        ok = len(last4) == 4 and (pd.Timestamp(day) - pd.Timestamp(last4[0]["end"])).days < 420
        eps = sum(x["eps"] for x in last4) if ok and all(x["eps"] is not None for x in last4) else None
        rev = sum(x["revenue"] for x in last4) if ok and all(x["revenue"] is not None for x in last4) else None
        sh = next((x["shares"] for x in reversed(known) if x["shares"]), None)
        dates.append(day)
        pe.append(round(float(price / eps), 2) if eps and eps > 0 else None)
        ps.append(round(float(price * sh / rev), 2) if rev and rev > 0 and sh else None)
    return {"dates": dates, "pe": pe, "ps": ps}


def valuation_annual(df, annual, lag_days=75):
    """India: P/E from each fiscal year's reported EPS, from 75 days after the year ends (when results are public)."""
    rows = [(pd.Timestamp(a["end"]) + pd.Timedelta(days=lag_days), a["eps"], a.get("revenue"), a.get("shares")) for a in annual if a.get("eps")]
    if len(rows) < 2:
        return None
    dates, pe, ps = [], [], []
    for d, price in df["close"].items():
        k = [x for x in rows if x[0] <= d]
        dates.append(d.strftime("%Y-%m-%d"))
        if not k:
            pe.append(None); ps.append(None)
            continue
        _, eps, rev, sh = k[-1]
        pe.append(round(float(price / eps), 2) if eps and eps > 0 else None)
        ps.append(round(float(price * sh / (rev * 10)), 2) if rev and sh and rev > 0 else None)     # shares in millions, revenue in crore (1 crore = 10 million)
    return {"dates": dates, "pe": pe, "ps": ps}


def adjust_splits(rows, splits):
    """Filings state share counts and per-share figures as they were when filed; a later stock split makes them look like a jump.
    Restate each one to today's shares: only splits after the day the figure was filed apply (a later filing is already adjusted)."""
    for r in rows:
        for key, inv in (("shares", False), ("eps", True)):
            f, v = r.pop(key + "_f", None), r.get(key)
            if v is None or not f:
                continue
            fac = 1.0
            for d, ratio in splits:
                if d.strftime("%Y-%m-%d") > f:
                    fac *= ratio
            r[key] = v / fac if inv else v * fac


def build(mk, sym):
    y = sym if mk == "US" else sym + ".NS"
    y = y.replace(".", "-") if mk == "US" and "." in y else y
    out = {"sym": sym, "mkt": mk, "built": int(time.time()), "notes": []}
    financial = False
    try:
        from us import universe as U
        financial = ((U.U["list"].get(sym) or {}).get("sector") == "Financials") if mk == "US" else False
    except Exception:
        pass
    df = splits = divs = meta = None
    try:
        df, splits, divs, meta = YF.weekly(y)
    except Exception as e:
        out["notes"].append(f"Price history unavailable ({type(e).__name__}).")
    out["currency"] = (meta or {}).get("currency") or ("USD" if mk == "US" else "INR")
    if mk == "US":
        f = None
        try:
            f = SEC.fundamentals(sym)
        except Exception as e:
            out["notes"].append(f"SEC filings unavailable ({type(e).__name__}).")
        if f:
            if splits:
                adjust_splits(f["annual"], splits)
                adjust_splits(f["quarterly"], splits)
            out.update(source="SEC filings (EDGAR), in $ million; per-share figures restated for splits", unit="$ million", annual=f["annual"], quarterly=f["quarterly"])
            if df is not None:
                out["valuation"] = valuation_us(df, splits, f["pit"])
        else:
            out.update(source="no SEC filings found for this ticker", unit="$ million", annual=[], quarterly=[])
    else:
        st = None
        try:
            st = YF.statements(y)
        except Exception as e:
            out["notes"].append(f"Yahoo statements unavailable ({type(e).__name__}).")
        ann, qs = (st or {}).get("annual", []), (st or {}).get("quarterly", [])
        for rows in (ann, qs):
            for r in rows:
                for k in YF.MONEY:
                    if r.get(k) is not None:
                        r[k] = r[k] / CRORE
                if r.get("capex") is not None:
                    r["capex"] = abs(r["capex"])
                if r.get("div") is not None:
                    r["div"] = abs(r["div"])
                if r.get("shares") is not None:
                    r["shares"] = r["shares"] / 1e6
        out.update(source="Yahoo company statements (about 4 fiscal years), in ₹ crore", unit="₹ crore", annual=ann, quarterly=qs)
        if df is not None and ann:
            out["valuation"] = valuation_annual(df, ann)
            out["notes"].append("India valuation history uses each year's reported EPS from Yahoo and can look off around splits and bonus issues.")
    out["ratios"] = ratios(out.get("annual") or [], financial)
    out["financial"] = financial
    v = out.get("valuation")
    if v:
        out["pe_stats"], out["ps_stats"] = _stats(v["pe"], next((x for x in reversed(v["pe"]) if x is not None), None)), _stats(v["ps"], next((x for x in reversed(v["ps"]) if x is not None), None))
        # start where there is data (India has about four years of earnings), and keep the payload small: every other week
        first = next((i for i in range(len(v["dates"])) if v["pe"][i] is not None or v["ps"][i] is not None), 0)
        out["valuation"] = {k: x[first::2] for k, x in v.items()}
    if df is not None:
        c = df["close"]
        out["price"] = {"dates": [d.strftime("%Y-%m-%d") for d in df.index][::1], "close": [round(float(x), 2) for x in c], "sma200": [None if np.isnan(x) else round(float(x), 2) for x in c.rolling(40).mean()],
                        "high52": round(float(c.iloc[-52:].max()), 2), "low52": round(float(c.iloc[-52:].min()), 2), "last": round(float(c.iloc[-1]), 2)}
        out["price"]["note"] = "Weekly closes; the line is the 40-week average (about 200 days)."
        out["dividends"] = [{"date": d.strftime("%Y-%m-%d"), "amount": round(a, 4)} for d, a in (divs or [])][-40:]
        out["splits"] = [{"date": d.strftime("%Y-%m-%d"), "ratio": r} for d, r in (splits or [])]
    out["events"] = EV.events(mk, sym, y)
    out["ownership"] = EV.ownership(mk, sym, y)
    return out


def detail(mk, sym, fresh=False):
    sym = sym.upper()
    p = DIR / f"{mk}-{sym}.json"
    if not fresh and p.exists() and time.time() - p.stat().st_mtime < 12 * 3600:
        return json.loads(p.read_text())
    r = build(mk, sym)
    p.write_text(json.dumps(r, default=float))
    return r
