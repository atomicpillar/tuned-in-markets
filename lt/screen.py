"""The long-term screener: every stock of the S&P 1500 (US) and the Nifty 500 (India), ranked on quality, growth, value,
trend and shareholder returns, from reported figures only.

US: SEC's bulk XBRL "frames" (one call returns one reported figure for every company), five calendar years, so a company
with a September year-end is matched to the nearest calendar year. India: Yahoo's company statements, about four fiscal years.
Each score is a percentile rank inside the universe (100 = best), averaged over the factors that exist; a missing factor is
skipped, never filled. The rank is a way to shortlist, not a forecast: the universe is today's index members (survivors), and
the figures are as reported."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np
import pandas as pd

from us import market as M
from us import research as R
from . import sec as SEC
from . import stock as ST
from . import yf as YF

DIR = M.DATA
BUILD = {"US": {"state": "idle", "msg": ""}, "IN": {"state": "idle", "msg": ""}}
TABLE = {"US": None, "IN": None}
W = {"quality": 30, "growth": 25, "value": 25, "trend": 10, "holders": 10}


def _frame(tag, unit, period, taxonomy="us-gaap"):
    d = R._sec(f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json", 60)
    return {x["cik"]: x["val"] for x in d["data"]}


def _merged(tags, unit, period):
    """One reported figure per company for the period; the first tag a company uses wins."""
    out = {}
    for t in tags:
        try:
            for cik, v in _frame(t, unit, period).items():
                out.setdefault(cik, v)
        except Exception:
            pass
        time.sleep(0.11)
    return out


def us_figures(log=print):
    """{cik: [annual rows oldest first]} from the SEC's bulk frames, five calendar years, in $ million."""
    y1 = date.today().year - 1
    years = list(range(y1 - 4, y1 + 1))
    # the newest year is complete only once most companies have filed: use it if thousands reported, else step back a year
    probe = _merged(["NetIncomeLoss"], "USD", f"CY{years[-1]}")
    if len(probe) < 3000:
        years = [y - 1 for y in years]
    table = {}
    flows = {"revenue": SEC.REV[:5], "gross": ["GrossProfit"], "opinc": ["OperatingIncomeLoss"], "net": SEC.TAGS["net"][0][:2], "ocf": SEC.TAGS["ocf"][0], "capex": SEC.TAGS["capex"][0],
             "div": SEC.TAGS["div"][0]}
    for i, y in enumerate(years):
        log(f"screener US: SEC figures for {y}")
        rows = {}
        for name, tags in flows.items():
            for cik, v in _merged(tags, "USD", f"CY{y}").items():
                rows.setdefault(cik, {})[name] = v / 1e6
        for cik, v in _merged(SEC.TAGS["eps"][0], "USD-per-shares", f"CY{y}").items():
            rows.setdefault(cik, {})["eps"] = v
        for cik, v in _merged(SEC.TAGS["shares"][0], "shares", f"CY{y}").items():
            rows.setdefault(cik, {})["shares"] = v / 1e6
        for name, (tags, unit) in SEC.INST.items():
            for cik, v in _merged(tags, unit, f"CY{y}Q4I").items():
                rows.setdefault(cik, {})[name] = v / 1e6
        for cik, r in rows.items():
            r["fy"] = str(y)
            r["end"] = f"{y}-12-31"
            r["fcf"] = r["ocf"] - r["capex"] if "ocf" in r and "capex" in r else None
            table.setdefault(cik, []).append(r)
    return table, years


def cik_map():
    p = DIR / "sec_tickers.json"
    try:
        d = json.loads(p.read_text())
        if time.time() - d["t"] > 30 * 86400:
            raise ValueError
    except Exception:
        raw = R._sec("https://www.sec.gov/files/company_tickers.json")
        d = {"t": time.time(), "m": {v["ticker"].upper(): v["cik_str"] for v in raw.values()}}
        p.write_text(json.dumps(d))
    return d["m"]


def _market_us(sym, quotes, hist):
    q = quotes.get(sym) or {}
    h = hist.get(sym)
    m = {"price": q.get("regularMarketPrice"), "mcap": (q.get("marketCap") or 0) / 1e6 or None, "div_yield": (q.get("trailingAnnualDividendYield") or 0) * 100 or None}
    return m, h


def _ret12(h):
    """12-month price move skipping the latest month (the standard momentum measure), from about one year of daily bars."""
    if h is None or len(h) < 235:
        return None
    c = h["close"]
    return round((float(c.iloc[-22]) / float(c.iloc[-253] if len(c) >= 253 else c.iloc[0]) - 1) * 100, 1)


def _trend(h, b12=None):
    """Price-based readings from the daily bars the dashboard keeps (about one year): momentum, the Weinstein stage, the
    ingredients of the Minervini trend template and of dual momentum. A figure that cannot be computed stays missing."""
    if h is None or len(h) < 130:
        return {}
    c, hi = h["close"], h["high"]
    lo = h["low"] if "low" in h else c            # older saved history has no lows: the lowest close stands in
    n = len(c)
    last = float(c.iloc[-1])
    hi52, lo52 = float(hi.iloc[-252:].max()), float(lo.iloc[-252:].min())
    out = {"from_high": round((last / hi52 - 1) * 100, 1)}
    s50 = float(c.iloc[-50:].mean())
    if n >= 200:
        out["above200"] = bool(last > float(c.iloc[-200:].mean()))
    r12 = _ret12(h)
    if r12 is not None:
        out["ret12"] = r12
    out["ret6"] = round((float(c.iloc[-22]) / float(c.iloc[-127]) - 1) * 100, 1)
    # Weinstein stage on the 30-week (150-day) average: 1 base, 2 advance, 3 top, 4 decline
    if n >= 172:
        m150 = c.rolling(150).mean()
        slope, above = float(m150.iloc[-1] / m150.iloc[-21] - 1), last > float(m150.iloc[-1])
        out["stage"] = (2 if slope > 0 else 3) if above else (4 if slope < 0 else 1)
    # relative-strength raw score: 3, 6, 9 and 12-month returns weighted 40/20/20/20 (re-weighted when a period is missing)
    parts = [(w, last / float(c.iloc[-1 - d]) - 1) for d, w in ((63, .4), (126, .2), (189, .2), (min(n - 1, 251), .2)) if n > d + 1]
    if len(parts) >= 2:
        out["rs_raw"] = round(sum(w * r for w, r in parts) / sum(w for w, _ in parts) * 100, 2)
    # the seven price tests of the Minervini trend template (the eighth, relative strength 70+, is added once ratings exist)
    if n >= 222:
        s150, s200, s200_old = float(c.iloc[-150:].mean()), float(c.iloc[-200:].mean()), float(c.iloc[-222:-22].mean())
        t = [last > s150 and last > s200, s150 > s200, s200 > s200_old, s50 > s150 > s200, last > s50, last >= 1.25 * lo52, last >= .75 * hi52]
        out["mino_base"] = int(sum(bool(x) for x in t))
    if r12 is not None:
        out["abs_mom"] = bool(r12 > 0)
        if b12 is not None:
            out["dual"] = bool(r12 > 0 and r12 > b12)
    return out


def piotroski(annual):
    """Piotroski's nine yes/no tests of financial strength. Returns (tests passed, tests that could be run); needs two years of data."""
    if len(annual) < 2:
        return None, 0
    a, p = annual[-1], annual[-2]
    ok = lambda *xs: all(x is not None for x in xs)
    t = []
    if ok(a.get("net"), a.get("assets")) and a["assets"]: t.append(a["net"] / a["assets"] > 0)                                   # 1 profitable
    if a.get("ocf") is not None: t.append(a["ocf"] > 0)                                                                         # 2 positive operating cash flow
    if ok(a.get("net"), a.get("assets"), p.get("net"), p.get("assets")) and a["assets"] and p["assets"]: t.append(a["net"] / a["assets"] > p["net"] / p["assets"])   # 3 return on assets rising
    if ok(a.get("ocf"), a.get("net")): t.append(a["ocf"] > a["net"])                                                            # 4 cash earnings above accounting earnings
    if ok(a.get("debt"), a.get("assets"), p.get("debt"), p.get("assets")) and a["assets"] and p["assets"]: t.append(a["debt"] / a["assets"] < p["debt"] / p["assets"])   # 5 leverage falling
    if ok(a.get("cur_assets"), a.get("cur_liab"), p.get("cur_assets"), p.get("cur_liab")) and a["cur_liab"] and p["cur_liab"]: t.append(a["cur_assets"] / a["cur_liab"] > p["cur_assets"] / p["cur_liab"])   # 6 liquidity rising
    if ok(a.get("shares"), p.get("shares")) and p["shares"]: t.append(a["shares"] <= p["shares"] * 1.005)                      # 7 no new shares
    if ok(a.get("gross"), a.get("revenue"), p.get("gross"), p.get("revenue")) and a["revenue"] and p["revenue"]: t.append(a["gross"] / a["revenue"] > p["gross"] / p["revenue"])   # 8 gross margin rising
    if ok(a.get("revenue"), a.get("assets"), p.get("revenue"), p.get("assets")) and a["assets"] and p["assets"]: t.append(a["revenue"] / a["assets"] > p["revenue"] / p["assets"])   # 9 asset turnover rising
    return int(sum(t)), len(t)


def graham(r, annual):
    """Benjamin Graham's defensive-investor tests, as far as the data allows: (tests passed, tests run, Graham number)."""
    a = annual[-1] if annual else {}
    t = []
    if r.get("pe") is not None: t.append(r["pe"] <= 15)
    if r.get("pb") is not None: t.append(r["pb"] <= 1.5 or (r.get("pe") is not None and r["pe"] * r["pb"] <= 22.5))
    if a.get("cur_assets") and a.get("cur_liab"): t.append(a["cur_assets"] / a["cur_liab"] >= 2)
    if r.get("n_years_net"): t.append(r["profitable_years"] == r["n_years_net"])
    if a.get("div") is not None: t.append(a["div"] > 0)
    g = r.get("eps_cagr3") if r.get("eps_cagr3") is not None else r.get("net_cagr3")
    if g is not None: t.append(g > 0)
    num = None
    if a.get("eps") and a.get("equity") and a.get("shares") and a["eps"] > 0 and a["equity"] > 0 and a["shares"] > 0:
        num = round((22.5 * a["eps"] * (a["equity"] / a["shares"])) ** .5, 2)
    return int(sum(t)), len(t), num


def _row(sym, name, sector, annual, mkt, hist, financial, mcap_unit, b12=None):
    a = annual[-1] if annual else {}
    r = {"sym": sym, "name": name, "sector": sector or "Other", "price": mkt.get("price"), "mcap": mkt.get("mcap"), "fy": a.get("fy")}
    r.update(ST.ratios(annual, financial))
    mc = mkt.get("mcap")
    r["pe"] = round(mc / a["net"], 1) if mc and a.get("net") and a["net"] > 0 else None
    r["ps"] = round(mc / a["revenue"], 2) if mc and a.get("revenue") and a["revenue"] > 0 else None
    r["pb"] = round(mc / a["equity"], 2) if mc and a.get("equity") and a["equity"] > 0 else None
    r["earn_yield"] = round(a["net"] / mc * 100, 1) if mc and a.get("net") is not None else None
    r["fcf_yield"] = None if financial or not mc or a.get("fcf") is None else round(a["fcf"] / mc * 100, 1)
    r["div_yield"] = round(mkt["div_yield"], 2) if mkt.get("div_yield") else None
    r.update(_trend(hist, b12))
    r["financial"] = financial
    if not financial:
        r["f_score"], r["f_n"] = piotroski(annual)
        ebit, ev = a.get("opinc"), (mc + (a.get("debt") or 0) - (a.get("cash") or 0)) if mc else None
        cap = (a["equity"] + (a.get("debt") or 0) - (a.get("cash") or 0)) if a.get("equity") is not None else None
        r["mf_ey"] = round(ebit / ev * 100, 1) if ebit is not None and ev and ev > 0 else None            # earnings yield: operating profit over enterprise value
        r["mf_roc"] = round(ebit / cap * 100, 1) if ebit is not None and cap and cap > 0 else None         # return on capital: operating profit over equity plus net debt
    gt, gn, gnum = graham(r, annual)
    r["graham"], r["graham_n"], r["graham_num"] = gt, gn, gnum
    g3 = r.get("eps_cagr3") if r.get("eps_cagr3") is not None else r.get("net_cagr3")
    r["peg"] = round(r["pe"] / g3, 2) if r.get("pe") and g3 and g3 > 0 else None
    return r


def _pct(vals, higher_better=True):
    """Percentile rank 0..100 of each value among the non-missing ones; None stays None."""
    s = pd.Series(vals, dtype="float64")
    ok = s.notna()
    out = pd.Series([None] * len(s), dtype="object")
    if ok.sum() >= 20:
        rk = s[ok].rank(pct=True, method="average") * 100
        out[ok] = (rk if higher_better else 100 - rk + 100 / ok.sum()).round(0)
    return list(out)


def score(rows):
    """Add quality / growth / value / trend / holders scores and the weighted total."""
    def col(k, sign=1):
        return [None if r.get(k) is None or (isinstance(r.get(k), float) and np.isnan(r[k])) else sign * r[k] for r in rows]
    q_roe, q_om, q_nm, q_fm, q_de = _pct(col("roe")), _pct(col("op_margin")), _pct(col("net_margin")), _pct(col("fcf_margin")), _pct(col("debt_equity"), False)
    cons = _pct([None if not r.get("n_years_net") else r["profitable_years"] / r["n_years_net"] for r in rows])
    g_rev, g_eps, g_net, g_fcf = _pct(col("rev_cagr3")), _pct(col("eps_cagr3")), _pct(col("net_cagr3")), _pct(col("fcf_cagr3"))
    v_ey, v_fy, v_pb = _pct(col("earn_yield")), _pct(col("fcf_yield")), _pct(col("pb"), False)
    t_r12, t_r6, t_hi = _pct(col("ret12")), _pct(col("ret6")), _pct(col("from_high"))
    h_sh, h_dy = _pct(col("share_change3"), False), _pct(col("div_yield"))
    # relative-strength rating (1 to 99, the percentile of the weighted return), the Minervini count and the Magic Formula rank
    rs = _pct(col("rs_raw"))
    for i, r in enumerate(rows):
        r["rs_rating"] = None if rs[i] is None else int(max(1, min(99, rs[i])))
        r["mino"] = None if r.get("mino_base") is None or r["rs_rating"] is None else r["mino_base"] + (1 if r["rs_rating"] >= 70 else 0)
    mf = [r for r in rows if r.get("mf_ey") is not None and r.get("mf_roc") is not None]
    if len(mf) >= 20:
        ey = {id(r): k for k, r in enumerate(sorted(mf, key=lambda r: -r["mf_ey"]))}
        rc = {id(r): k for k, r in enumerate(sorted(mf, key=lambda r: -r["mf_roc"]))}
        for k, r in enumerate(sorted(mf, key=lambda r: (ey[id(r)] + rc[id(r)]))):
            r["mf_rank"] = k + 1
    avg = lambda xs: None if not [x for x in xs if x is not None] else round(float(np.mean([x for x in xs if x is not None])))
    for i, r in enumerate(rows):
        fin = r.get("financial")
        r["s_quality"] = avg([q_roe[i], q_nm[i] if fin else q_om[i], None if fin else q_fm[i], None if fin else q_de[i], cons[i]])
        r["s_growth"] = avg([g_rev[i], g_eps[i] if g_eps[i] is not None else g_net[i], None if fin else g_fcf[i]])
        r["s_value"] = avg([v_ey[i], v_pb[i] if fin else v_fy[i]])
        tr = [t_r12[i], t_r6[i], t_hi[i], None if r.get("above200") is None else (100 if r["above200"] else 0)]
        r["s_trend"] = avg(tr)
        r["s_holders"] = avg([h_sh[i], h_dy[i]])
        parts = {"quality": r["s_quality"], "growth": r["s_growth"], "value": r["s_value"], "trend": r["s_trend"], "holders": r["s_holders"]}
        have = {k: v for k, v in parts.items() if v is not None}
        r["score"] = round(sum(v * W[k] for k, v in have.items()) / sum(W[k] for k in have)) if len(have) >= 3 else None
    return rows


def build_us(log=print):
    from us import sector as SC
    from us import universe as U
    BUILD["US"].update(state="building", msg="reading the SEC's reported figures")
    table, years = us_figures(log)
    cm = cik_map()
    quotes, hist = SC.S["quotes"], U.U["hist"]
    b12 = _ret12(hist.get("IDX:^GSPC"))
    rows = []
    for sym, v in U.U["list"].items():
        cik = v.get("cik") or cm.get(sym.replace("-", ".").upper()) or cm.get(sym.upper())
        ann = sorted(table.get(int(cik), []) if cik else [], key=lambda r: r["fy"])
        if not ann:
            continue
        financial = v["sector"] == "Financials"
        mk, h = _market_us(sym, quotes, hist)
        rows.append(_row(sym, v["name"], v["sector"], ann, mk, h, financial, "$M", b12))
    rows = score(rows)
    out = {"built": int(time.time()), "mkt": "US", "unit": "$ million", "years": years, "n": len(rows),
           "universe": "S&P 1500 (today's members)", "source": "SEC XBRL filings (bulk frames, calendar-year aligned), Yahoo prices"}
    TABLE["US"] = {**out, "rows": rows}
    (DIR / "lt_screen_US.json").write_text(json.dumps(TABLE["US"], default=float))
    BUILD["US"].update(state="ready", msg="")
    log(f"screener US: {len(rows)} companies ranked")


def build_in(log=print):
    from sx import universe as IU
    from us import yahoo as Y
    BUILD["IN"].update(state="building", msg="reading company statements")
    syms = sorted(IU.U["list"]) or sorted(IU.nifty500())
    try:
        quotes = Y.quotes([s + ".NS" for s in syms])
    except Exception:
        quotes = {}
    done = {"n": 0}
    stm = {}

    def one(s):
        try:
            stm[s] = YF.statements(s + ".NS")["annual"]
        except Exception:
            pass
        done["n"] += 1
        BUILD["IN"]["msg"] = f"company statements {done['n']}/{len(syms)}"
        if done["n"] % 100 == 0:
            log(f"screener IN: statements {done['n']}/{len(syms)}")
        time.sleep(0.1)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, syms))
    rows = []
    for s in syms:
        ann = stm.get(s) or []
        if not ann:
            continue
        for r in ann:
            for k in YF.MONEY:
                if r.get(k) is not None:
                    r[k] = r[k] / 1e7
            if r.get("capex") is not None:
                r["capex"] = abs(r["capex"])
            if r.get("div") is not None:
                r["div"] = abs(r["div"])
            if r.get("shares") is not None:
                r["shares"] = r["shares"] / 1e6
        c = IU.U["cls"].get(s) or {}
        info = IU.U["list"].get(s) or {}
        q = quotes.get(s + ".NS") or {}
        mk = {"price": q.get("regularMarketPrice"), "mcap": (q.get("marketCap") or 0) / 1e7 or None, "div_yield": (q.get("trailingAnnualDividendYield") or 0) * 100 or None}
        sector = c.get("sector") or info.get("industry")
        rows.append(_row(s, c.get("name") or info.get("name") or s, sector, ann, mk, IU.U["hist"].get(s), sector == "Financial Services", "₹ cr", _ret12(IU.U["hist"].get("IDX:NIFTY 50"))))
    rows = score(rows)
    out = {"built": int(time.time()), "mkt": "IN", "unit": "₹ crore", "years": [], "n": len(rows), "universe": "Nifty 500 (today's members)",
           "source": "Yahoo company statements (about 4 fiscal years), Yahoo prices"}
    TABLE["IN"] = {**out, "rows": rows}
    (DIR / "lt_screen_IN.json").write_text(json.dumps(TABLE["IN"], default=float))
    BUILD["IN"].update(state="ready", msg="")
    log(f"screener IN: {len(rows)} companies ranked")


def load(mk):
    if TABLE[mk] is None:
        try:
            TABLE[mk] = json.loads((DIR / f"lt_screen_{mk}.json").read_text())
            BUILD[mk]["state"] = "ready"
        except Exception:
            pass
    return TABLE[mk]


def ensure(mk, log=print):
    """Build the table when there is none or it is a week old (called from a background thread)."""
    t = load(mk)
    if t and time.time() - t["built"] < 7 * 86400:
        return
    try:
        (build_us if mk == "US" else build_in)(log)
    except Exception as e:
        BUILD[mk].update(state="error", msg=f"{type(e).__name__}: {e}")
        log(f"screener {mk}: {type(e).__name__}: {e}")


# Named methods analysts use, each a filter and an ordering over the same table: (keep, sort key (smaller first), value to show)
METHODS = {
    "piotroski": (lambda r: r.get("f_score") is not None and r["f_n"] >= 7 and r["f_score"] >= 7, lambda r: (-r["f_score"], -(r.get("score") or 0)), lambda r: f'{r["f_score"]}/{r["f_n"]}'),
    "magic": (lambda r: r.get("mf_rank") is not None, lambda r: r["mf_rank"], lambda r: f'#{r["mf_rank"]}'),
    "minervini": (lambda r: r.get("mino") == 8, lambda r: -(r.get("rs_rating") or 0), lambda r: f'{r["mino"]}/8'),
    "stage2": (lambda r: r.get("stage") == 2, lambda r: -(r.get("rs_rating") or 0), lambda r: f'Stage {r["stage"]}'),
    "rs80": (lambda r: (r.get("rs_rating") or 0) >= 80, lambda r: -r["rs_rating"], lambda r: f'RS {r["rs_rating"]}'),
    "dual": (lambda r: r.get("dual"), lambda r: -(r.get("ret12") or 0), lambda r: f'{r["ret12"]:+.0f}% 12m'),
    "graham": (lambda r: r["graham_n"] >= 4 and r["graham"] >= 4, lambda r: (-r["graham"], r.get("pe") or 999), lambda r: f'{r["graham"]}/{r["graham_n"]}'),
    "peg": (lambda r: r.get("peg") is not None and 0 < r["peg"] < 1.5, lambda r: r["peg"], lambda r: f'PEG {r["peg"]}'),
}


def view(mk, sort="score", order="desc", sector="", minmcap=0, q="", limit=100, offset=0, only_profitable=False, method=""):
    t = load(mk)
    if not t:
        return {"state": BUILD[mk]["state"], "msg": BUILD[mk]["msg"] or "The screener is being built (first run, a few minutes).", "rows": []}
    rows = t["rows"]
    if sector:
        rows = [r for r in rows if r["sector"] == sector]
    if minmcap:
        rows = [r for r in rows if r.get("mcap") and r["mcap"] >= minmcap]
    if only_profitable:
        rows = [r for r in rows if r.get("net_margin") is not None and r["net_margin"] > 0]
    if q:
        qq = q.upper()
        rows = [r for r in rows if qq in r["sym"] or qq in (r["name"] or "").upper()]
    if method in METHODS:
        keep, key, show = METHODS[method]
        rows = sorted([r for r in rows if keep(r)], key=key)
        rows = [{**r, "mv": show(r)} for r in rows]
        sectors = sorted({r["sector"] for r in t["rows"]})
        return {"state": "ready", "built": t["built"], "unit": t["unit"], "universe": t["universe"], "source": t["source"], "years": t["years"], "total": t["n"],
                "matching": len(rows), "sectors": sectors, "weights": W, "method": method, "rows": rows[offset:offset + limit]}

    def key(r):
        v = r.get(sort)
        return (v is None, -(v if isinstance(v, (int, float)) else 0) if order == "desc" else (v if isinstance(v, (int, float)) else 0))
    if sort in ("sym", "name", "sector"):
        rows = sorted(rows, key=lambda r: str(r.get(sort) or ""), reverse=order == "desc")
    else:
        rows = sorted(rows, key=key)
    sectors = sorted({r["sector"] for r in t["rows"]})
    return {"state": "ready", "built": t["built"], "unit": t["unit"], "universe": t["universe"], "source": t["source"], "years": t["years"], "total": t["n"],
            "matching": len(rows), "sectors": sectors, "weights": W, "rows": rows[offset:offset + limit]}
