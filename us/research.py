"""A one-page, plain-language research note for any US stock: what the company does, how its results are moving,
its finances, valuation against peers, the industry and the economy around it, a SWOT and an overall score out
of 100. Same page and same keys as the India note (lab/research.py); money amounts are in $ million.

Built from the SEC's own filings (EDGAR XBRL, free and official), Yahoo's company summary and quote data,
Wikipedia and a few market prices. Rules-based (no opinions are invented); cached for 12 hours per stock."""
import envfile
import json
import re
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from lab.research import clip, lin
from . import industries as I
from . import market as M
from . import sector as SC
from . import universe as U
from . import yahoo as Y

DIR = M.DATA / "us_research"
DIR.mkdir(exist_ok=True)
MACRO_SYMS = {"oil": "CL=F", "rates": "^TNX", "usd": "DX-Y.NYB", "metals": "HG=F", "us": "^GSPC"}
_MACRO = {"t": 0, "v": {}}
REV_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenues", "SalesRevenueNet",
            "RevenuesNetOfInterestExpense", "InterestAndDividendIncomeOperating"]


def _sec(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=envfile.sec_headers()), timeout=timeout) as r:
        return json.loads(r.read())


def cik_of(sym):
    c = (U.U["list"].get(sym) or {}).get("cik")
    if c:
        return int(c)
    p = M.DATA / "sec_tickers.json"
    try:
        d = json.loads(p.read_text())
        if time.time() - d["t"] > 30 * 86400:
            raise ValueError
    except Exception:
        raw = _sec("https://www.sec.gov/files/company_tickers.json")
        d = {"t": time.time(), "m": {v["ticker"].upper(): v["cik_str"] for v in raw.values()}}
        p.write_text(json.dumps(d))
    return d["m"].get(sym.replace("-", ".").upper()) or d["m"].get(sym.upper())


def _days(a, b):
    return (pd.Timestamp(b) - pd.Timestamp(a)).days


def _one(facts, tag, unit):
    """Discrete quarters of one XBRL tag: 3-month values as filed, and the fourth quarter as the year minus the other three."""
    rows = (((facts.get("us-gaap") or {}).get(tag) or {}).get("units") or {}).get(unit)
    if not rows:
        return {}
    best = {}
    for r in rows:
        if "start" not in r:
            continue
        k = (r["start"], r["end"])
        if k not in best or r["filed"] > best[k]["filed"]:
            best[k] = r
    q = {r["end"]: r["val"] for (s, e), r in best.items() if 80 <= _days(s, e) <= 100}
    for (s, e), r in best.items():
        if 350 <= _days(s, e) <= 380 and e not in q:
            inside = sorted(x for x in q if s < x < e and _days(s, x) < 300)
            if len(inside) >= 3:
                q[e] = r["val"] - sum(q[x] for x in inside[-3:])
    return q


def _series(facts, tags, unit="USD"):
    """Quarters merged across every tag a company has used over the years: the first tag in the list wins for a given quarter."""
    out = {}
    for tag in tags:
        for e, v in _one(facts, tag, unit).items():
            out.setdefault(e, v)
    return dict(sorted(out.items())[-8:])


# companies that moved into a new holding company keep their earlier filings under the old CIK
PREDECESSOR = {2115436: 34088}


def _facts(cik):
    return _sec(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")["facts"]


def quarters(sym):
    """Last 8 consecutive quarters from SEC filings, in $ million."""
    cik = cik_of(sym)
    if not cik:
        return []
    sets = [_facts(cik)]
    if int(cik) in PREDECESSOR:
        sets.append(_facts(PREDECESSOR[int(cik)]))
    rev, ni, eps = {}, {}, {}
    for facts in sets:                       # the newest filer first: it wins where both have a quarter
        for dst, src in ((rev, _series(facts, REV_TAGS)), (ni, _series(facts, ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"])),
                         (eps, _series(facts, ["EarningsPerShareDiluted", "EarningsPerShareBasic"], "USD/shares"))):
            for e, v in src.items():
                dst.setdefault(e, v)
    ends = sorted(set(rev) | set(ni))
    if rev and ni and not set(ends[-8:]) & set(rev):      # a stale revenue tag must not hide current profit
        rev = {}
    run = ends[-1:]                           # keep only the latest unbroken run of quarters: a 12-month total must be 12 months
    for e in reversed(ends[:-1]):
        if _days(e, run[0]) > 120:
            break
        run.insert(0, e)
    out = []
    for e in run[-8:]:
        d = pd.Timestamp(e)
        out.append({"q": e, "kind": "SEC", "date": e, "label": d.strftime("%b %y"), "income": rev.get(e) / 1e6 if e in rev else None,
                    "profit": ni.get(e) / 1e6 if e in ni else None, "pbt": None, "eps": eps.get(e)})
    return out


def profile(sym):
    try:
        return Y.summary(sym, "assetProfile,financialData,defaultKeyStatistics,summaryDetail,price")
    except Exception:
        return {}


def _raw(d, k):
    v = (d or {}).get(k)
    return v.get("raw") if isinstance(v, dict) else v


def wiki(name):
    if not name:
        return None
    short = re.sub(r"\b(inc\.?|corporation|corp\.?|company|co\.?|ltd\.?|plc|holdings|group)\b", "", name, flags=re.I).strip(" .,")
    try:
        s = M.get_json("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=3&srsearch=" + urllib.parse.quote(f"{short} company"), 15)
        for hit in s.get("query", {}).get("search", []):
            words = [w for w in re.findall(r"[a-z]+", short.lower()) if len(w) > 2][:3]
            if not any(w in hit["title"].lower() for w in words):
                continue
            p = M.get_json("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(hit["title"].replace(" ", "_")), 15)
            ext = p.get("extract") or ""
            if ext:
                return {"text": " ".join(re.split(r"(?<=[.!?])\s+", ext)[:3]), "url": (p.get("content_urls") or {}).get("desktop", {}).get("page"), "title": hit["title"]}
    except Exception:
        return None
    return None


def macro():
    if time.time() - _MACRO["t"] < 6 * 3600 and _MACRO["v"]:
        return _MACRO["v"]
    out = {}
    for k, y in MACRO_SYMS.items():
        try:
            d = M.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(y)}?interval=1d&range=6mo", 15)["chart"]["result"][0]
            c = [x for x in d["indicators"]["quote"][0]["close"] if x]
            out[k] = {"now": round(c[-1], 2), "chg3m": round((c[-1] / c[-64] - 1) * 100, 1) if len(c) > 64 else None}
        except Exception:
            pass
    _MACRO.update(t=time.time(), v=out)
    return out


def _ret(sym, days):
    h = U.U["hist"].get(sym)
    if h is None or len(h) <= days:
        return None
    c = h["close"].values
    return round(float((c[-1] / c[-1 - days] - 1) * 100), 1)


def peers(sym, c):
    cls = U.U["cls"]
    same = [(k, v) for k, v in cls.items() if v.get("basic") == c.get("basic") and k != sym and v.get("mcap")]
    if len(same) >= 3:
        same.sort(key=lambda kv: -(kv[1].get("mcap") or 0))
    else:                                              # no sub-industry mates: the sector's stocks closest in size
        same = [(k, v) for k, v in cls.items() if v.get("sector") == c.get("sector") and k != sym and v.get("mcap")]
        me = max(c.get("mcap") or 1, 1)
        same.sort(key=lambda kv: abs(np.log((kv[1].get("mcap") or 1) / me)))
    return [{"sym": k, "name": (v.get("name") or k)[:28], "mcap_cr": round((v.get("mcap") or 0) / 1e6), "pe": round(v["pe"], 1) if v.get("pe") else None} for k, v in same[:6]]


def sector_strength(sym, c):
    mates = [k for k, v in U.U["cls"].items() if v.get("sector") == c.get("sector")]
    r = [x for x in (_ret(k, 63) for k in mates[:60]) if x is not None]
    b = _ret("IDX:^GSPC", 63)
    return {"sector": c.get("sector"), "sector_3m": round(float(np.median(r)), 1) if r else None, "nifty_3m": b,
            "rel": round(float(np.median(r)) - b, 1) if r and b is not None else None, "n": len(r)}


def sector_pe(c):
    pes = [v["pe"] for v in U.U["cls"].values() if v.get("sector") == c.get("sector") and v.get("pe") and 0 < v["pe"] < 150]
    return round(float(np.median(pes)), 1) if len(pes) >= 5 else None


def build(sym):
    sym = sym.upper().replace(".", "-")
    meta = U.U["list"].get(sym) or U.U["all"].get(sym) or {}
    c = dict(U.U["cls"].get(sym) or {})
    prof = profile(sym)
    ap, fd, ks, sd, pr_ = (prof.get(k) or {} for k in ("assetProfile", "financialData", "defaultKeyStatistics", "summaryDetail", "price"))
    name = c.get("name") or pr_.get("longName") or pr_.get("shortName") or meta.get("name") or sym
    sector = c.get("sector") or {"Technology": "Information Technology", "Financial Services": "Financials", "Healthcare": "Health Care", "Consumer Cyclical": "Consumer Discretionary",
                                  "Consumer Defensive": "Consumer Staples", "Basic Materials": "Materials"}.get(ap.get("sector"), ap.get("sector") or "Other")
    sub = c.get("basic") or ap.get("industry") or ""
    mcap = c.get("mcap") or _raw(pr_, "marketCap") or 0
    pe = c.get("pe") or _raw(sd, "trailingPE")
    high52, low52 = c.get("high52") or _raw(sd, "fiftyTwoWeekHigh"), c.get("low52") or _raw(sd, "fiftyTwoWeekLow")
    ltp = (SC.price(sym) or {}).get("ltp") or _raw(pr_, "regularMarketPrice")
    c.update(sector=sector, basic=sub, mcap=mcap)
    what, drivers = I.lookup(sub, sector)
    desc = ap.get("longBusinessSummary")
    company = " ".join(re.split(r"(?<=[.!?])\s+", desc)[:2]) if desc else what
    try:
        fin = quarters(sym)
    except Exception:
        fin = []
    de = _raw(fd, "debtToEquity")
    de = de / 100 if de is not None else None
    if de is not None and not 0 <= de <= 15:          # negative equity or a data glitch: better no number than a silly one
        de = None
    bal = {"de": round(de, 2) if de is not None else None, "icr": None, "as_of": None, "interest": 0, "dep": 0}
    wk = wiki(name)
    mac = macro()
    sec = sector_strength(sym, c)
    pr = peers(sym, c)
    spe = sector_pe(c)
    mcap_m = mcap / 1e6
    fs = sector == "Financials"

    inc = [x["income"] for x in fin if x["income"] is not None]
    pat = [x["profit"] for x in fin if x["profit"] is not None]
    ttm_inc = sum(inc[-4:]) if len(inc) >= 4 else None
    ttm_pat = sum(pat[-4:]) if len(pat) >= 4 else None
    byd = {x["date"][:7]: x for x in fin}
    pairs = []
    for x in fin[-4:]:
        d0 = pd.Timestamp(x["date"]) - pd.DateOffset(years=1)
        y = next((v for k, v in byd.items() if abs((pd.Timestamp(k + "-01") - pd.Timestamp(str(d0.date())[:7] + "-01")).days) <= 31), None)
        if y:
            pairs.append((x, y))

    def growth(key):
        a = [(x[key], y[key]) for x, y in pairs if x[key] is not None and y[key] is not None]
        if not a:
            return None
        now, then = sum(u for u, _ in a), sum(v for _, v in a)
        return (now / then - 1) * 100 if then > 0 else None
    g_inc, g_pat = growth("income"), growth("profit")
    n_pairs = len(pairs)
    q_yoy = None
    if len(fin) >= 5 and fin[-1]["profit"] is not None and fin[-5]["profit"] and fin[-5]["profit"] > 0:
        q_yoy = (fin[-1]["profit"] / fin[-5]["profit"] - 1) * 100
    margin = ttm_pat / ttm_inc * 100 if ttm_inc and ttm_pat is not None else None
    norm = I.MARGIN_NORM.get(sector, 8)
    profit_q = sum(1 for p in pat if p > 0)
    if (not pe or pe <= 0) and ttm_pat and ttm_pat > 0 and mcap_m:
        pe = mcap_m / ttm_pat

    tech = {}
    try:
        h = U.U["hist"].get(sym)
        if h is not None and len(h) > 200:
            cl = h["close"]
            sma200, sma50 = cl.iloc[-200:].mean(), cl.iloc[-50:].mean()
            hh = float(h["high"].iloc[-250:].max())
            atr = float(((h["high"] - cl.shift()).abs()).iloc[-14:].mean()) if "high" in h else None
            b = _ret("IDX:^GSPC", 63)
            tech = {"uptrend": bool(cl.iloc[-1] > sma200 and sma50 > sma200), "rs63": round(_ret(sym, 63) - b, 1) if _ret(sym, 63) is not None and b is not None else None,
                    "from_high": round((float(cl.iloc[-1]) / hh - 1) * 100, 1), "atr_pct": round(float(((h["high"] - cl.shift()).abs().iloc[-14:].mean()) / cl.iloc[-1] * 100), 2),
                    "ret1y": _ret(sym, 250), "ret3m": _ret(sym, 63)}
    except Exception:
        pass

    econ, tail = [], 0
    thr = {"oil": 8, "rates": 5, "usd": 2, "metals": 5, "us": 3}
    for fac, eff, why in drivers:
        reading = mac.get(fac)
        push = None
        if reading and reading.get("chg3m") is not None and eff != 0:
            ch = reading["chg3m"]
            if abs(ch) >= thr.get(fac, 4):
                push = eff * (1 if ch > 0 else -1)
                tail += push
        elif reading and reading.get("chg3m") is not None and eff == 0 and abs(reading["chg3m"]) >= 10:
            push, tail = 0, tail - .5
        econ.append({"factor": fac, "name": I.FACTOR_NAMES.get(fac, fac), "effect": eff, "why": why, "reading": reading, "push": push})

    sc = {}
    size = lin(np.log10(max(mcap_m, 1)), 2.5, 6.0)               # $300 million .. $1 trillion
    cons = profit_q / max(len(pat), 1) * 10 if pat else None
    sc["Business"] = round(np.nanmean([x for x in (size, cons) if x is not None]), 1) if (size is not None or cons is not None) else None
    sc["Growth"] = round(np.nanmean([x for x in (lin(g_inc, -10, 25), lin(g_pat, -20, 40), lin(q_yoy, -30, 50)) if x is not None]), 1) if any(x is not None for x in (g_inc, g_pat, q_yoy)) else None
    sc["Profitability"] = lin(margin / norm if margin is not None else None, 0, 2)
    if fs:
        sc["Financial health"] = round(cons, 1) if cons is not None else None
    else:
        d = bal.get("de")
        de_s = None if d is None else (10 if d < .3 else 8 if d < .6 else 6 if d < 1 else 3.5 if d < 2 else 1)
        sc["Financial health"] = round(np.nanmean([x for x in (de_s, cons) if x is not None]), 1) if any(x is not None for x in (de_s, cons)) else None
    if pe and pe > 0 and spe:
        r = pe / spe
        v = 9 if r <= .7 else 7.5 if r <= .9 else 6 if r <= 1.1 else 4.5 if r <= 1.4 else 3 if r <= 2 else 1.5
        if g_pat is not None and g_pat > 25 and r < 1.6:
            v = min(10, v + 1.5)
        sc["Valuation"] = v
    else:
        sc["Valuation"] = 2 if ttm_pat is not None and ttm_pat <= 0 else None
    ind = lin(sec.get("rel"), -10, 10)
    sc["Industry & economy"] = round(clip((ind if ind is not None else 5) + tail * 1.5, 0, 10), 1)
    if tech:
        m = (4 if tech.get("uptrend") else 0) + (lin(tech.get("from_high"), -30, 0) or 0) * .3 + (3 if (tech.get("rs63") or 0) > 0 else 0)
        sc["Momentum"] = round(clip(m, 0, 10), 1)
    W = {"Business": 15, "Growth": 20, "Profitability": 15, "Financial health": 15, "Valuation": 15, "Industry & economy": 10, "Momentum": 10}
    have = {k: v for k, v in sc.items() if v is not None}
    total = round(sum(have[k] * W[k] for k in have) / sum(W[k] for k in have) * 10) if have else None
    grade = None if total is None else ("Strong" if total >= 75 else "Good" if total >= 62 else "Average" if total >= 48 else "Weak" if total >= 35 else "Poor")

    s_, w_, o_, t_ = [], [], [], []
    if g_pat is not None and g_pat > 20: s_.append(f"Profit is growing fast: up {g_pat:.0f}% on the same quarters a year earlier.")
    if g_inc is not None and g_inc > 15: s_.append(f"Sales are growing: up {g_inc:.0f}% on a year earlier.")
    if margin is not None and margin >= norm: s_.append(f"Keeps a healthy share of sales as profit ({margin:.1f}%, typical for its kind is ~{norm}%).")
    if pat and profit_q == len(pat) and len(pat) >= 6: s_.append(f"Made a profit in every one of the last {len(pat)} quarters.")
    if not fs and bal.get("de") is not None and bal["de"] < .3: s_.append("Very little debt against its own capital.")
    if pr and mcap_m and all(mcap_m >= p["mcap_cr"] for p in pr): s_.append("The biggest company in its industry group on the market.")
    if tech.get("rs63") and tech["rs63"] > 10: s_.append(f"The share has beaten the S&P 500 by {tech['rs63']:.0f} points over 3 months.")
    if margin is not None and margin < norm / 2: w_.append(f"Thin profit margin ({margin:.1f}% of sales), so small cost changes hurt.")
    if g_pat is not None and g_pat < -10: w_.append(f"Profit fell {abs(g_pat):.0f}% against a year earlier.")
    if g_inc is not None and g_inc < -5: w_.append(f"Sales shrank {abs(g_inc):.0f}% against a year earlier.")
    if pat and profit_q < len(pat): w_.append(f"Made a loss in {len(pat) - profit_q} of the last {len(pat)} quarters.")
    if not fs and bal.get("de") is not None and bal["de"] > 1.5: w_.append(f"Carries a lot of debt ({bal['de']:.1f}× its own capital).")
    if pe and spe and pe > 1.5 * spe: w_.append(f"Expensive: {pe:.0f}× its yearly profit against ~{spe:.0f}× for its sector.")
    if sec.get("rel") is not None and sec["rel"] > 3: o_.append(f"Its sector ({sec['sector']}) has beaten the S&P 500 by {sec['rel']:.0f} points over 3 months: money is flowing in.")
    for e in econ:
        if e["push"] == 1: o_.append(f"{e['name']} is moving in its favour ({e['why']}).")
        if e["push"] == -1: t_.append(f"{e['name']} is moving against it ({e['why']}).")
        if e["push"] == 0: t_.append(f"{e['name']} moved {e['reading']['chg3m']:+.0f}% in 3 months; big swings hurt it ({e['why']}).")
    if pe and spe and pe < .85 * spe and (g_pat or 0) > 0: o_.append(f"Cheaper than its sector ({pe:.0f}× vs ~{spe:.0f}× profit) while profit is still growing.")
    if tech.get("uptrend") and tech.get("from_high") is not None and tech["from_high"] > -8: o_.append("Share is in an uptrend and close to its 52-week high.")
    if any(e["factor"] == "reg" for e in econ): t_.append("Depends on government or regulator decisions (" + next(e["why"] for e in econ if e["factor"] == "reg") + ").")
    if any(e["factor"] == "china" for e in econ): t_.append("Exposed to China: export limits, local rivals or cheap imports.")
    if sec.get("rel") is not None and sec["rel"] < -3: t_.append(f"Its sector has lagged the S&P 500 by {abs(sec['rel']):.0f} points over 3 months.")
    if tech.get("atr_pct") and tech["atr_pct"] > 3.5: t_.append(f"The share swings a lot (about {tech['atr_pct']:.1f}% on a normal day).")
    if tech.get("from_high") is not None and tech["from_high"] < -30: t_.append(f"The share is {abs(tech['from_high']):.0f}% below its 52-week high.")

    big = (lambda m: f"${m / 1e6:,.2f} trillion" if m >= 1e6 else f"${m / 1e3:,.1f} billion" if m >= 1e3 else f"${m:,.0f} million")
    size_word = "mega-cap" if mcap_m >= 200000 else "very large" if mcap_m >= 50000 else "large" if mcap_m >= 10000 else "mid-sized" if mcap_m >= 2000 else "small" if mcap_m >= 300 else "very small"
    lines = [f"{name}: {company}", f"It is a {size_word} company: the market values the whole business at about {big(mcap_m)}."]
    if ttm_inc:
        lines.append(f"In the last 12 months it brought in {big(ttm_inc)} and kept {big(ttm_pat)} as profit"
                     + (f", about ${margin:.1f} of profit on every $100 of sales." if margin is not None else "."))
    if g_inc is not None or g_pat is not None:
        lines.append(("Compared with the same quarters a year earlier, " if n_pairs < 4 else "Compared with the 12 months before, ") + ", ".join(x for x in (
            f"income is {'up' if g_inc >= 0 else 'down'} {abs(g_inc):.0f}%" if g_inc is not None else None,
            f"profit is {'up' if g_pat >= 0 else 'down'} {abs(g_pat):.0f}%" if g_pat is not None else None) if x) + ".")
    if pe and pe > 0:
        cmp_ = "" if not spe else (", cheaper than" if pe < .9 * spe else ", more expensive than" if pe > 1.1 * spe else ", about the same as") + f" its sector (~{spe:.0f}×)"
        lines.append(f"At today's price you pay about {pe:.0f}× one year's profit{cmp_}.")
    return {"sym": sym, "name": name, "built": int(time.time()), "macro": None, "sector": sector, "industry": None, "basic": sub, "index": None, "what": what,
            "summary": lines, "wiki": wk, "mcap_cr": round(mcap_m), "pe": round(pe, 1) if pe else None, "sector_pe": spe, "delivery": None,
            "high52": high52, "low52": low52, "ltp": ltp, "results": fin,
            "ttm": {"income": ttm_inc, "profit": ttm_pat, "margin": round(margin, 1) if margin is not None else None, "g_inc": round(g_inc, 1) if g_inc is not None else None,
                    "g_pat": round(g_pat, 1) if g_pat is not None else None, "q_yoy": round(q_yoy, 1) if q_yoy is not None else None, "norm": norm,
                    "pairs": n_pairs, "profit_q": profit_q, "n_q": len(pat)},
            "balance": bal, "financial": fs, "peers": pr, "sector_strength": sec, "economy": econ, "tech": tech, "scores": sc, "weights": W, "total": total, "grade": grade,
            "swot": {"Strengths": s_ or ["Nothing stands out."], "Weaknesses": w_ or ["No obvious weak spot in the numbers."],
                     "Opportunities": o_ or ["No clear tailwind right now."], "Threats": t_ or ["No clear headwind right now."]},
            "sources": ["SEC filings (EDGAR)", "Yahoo company summary and quotes", "Wikipedia", "Yahoo (crude, Treasury yield, dollar, copper, S&P 500)"]}


def report(sym, fresh=False):
    sym = sym.upper().replace(".", "-")
    p = DIR / f"{sym}.json"
    if not fresh and p.exists() and time.time() - p.stat().st_mtime < 12 * 3600:
        return json.loads(p.read_text())
    r = build(sym)
    p.write_text(json.dumps(r, default=float))
    return r
