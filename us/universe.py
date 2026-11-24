"""The US stocks behind the map: the S&P 1500 (large, mid and small caps, each with its GICS sector and
sub-industry), the Nasdaq-100, and every US-listed symbol from Nasdaq's own directory for the full scanner.
Lists are public and cached on disk for a week. A year of daily bars per stock (Yahoo, refreshed daily)
feeds week / month / 3-month moves, the 50-day average, normal volume and the sector histories, built slowly
in the background like the India side."""
import csv
import io
import json
import time
import urllib.parse

import numpy as np
import pandas as pd

from . import market as M

LISTS = M.DATA / "us_lists.json"
HIST = M.DATA / "us_history"
HIST.mkdir(exist_ok=True)

# the 20 sectors on the US map: the 11 GICS sectors plus 9 themes, each tracked by its SPDR / iShares ETF on Yahoo.
# Members come from the GICS sub-industry (or a named list where no sub-industry fits), like the India map.
SECTORS = [
    {"name": "Tech", "index": "XLK", "group": "Tech & media", "sector": ["Information Technology"], "not_sub": ["Semiconductors", "Semiconductor Materials & Equipment", "Application Software", "Systems Software"]},
    {"name": "Semis", "index": "SMH", "group": "Tech & media", "sub": ["Semiconductors", "Semiconductor Materials & Equipment"]},
    {"name": "Software", "index": "IGV", "group": "Tech & media", "sub": ["Application Software", "Systems Software"]},
    {"name": "Comm Services", "index": "XLC", "group": "Tech & media", "sector": ["Communication Services"]},
    {"name": "Financials", "index": "XLF", "group": "Financials", "sector": ["Financials"], "not_sub": ["Regional Banks"]},
    {"name": "Reg Banks", "index": "KRE", "group": "Financials", "sub": ["Regional Banks"]},
    {"name": "Health Care", "index": "XLV", "group": "Healthcare", "sector": ["Health Care"], "not_sub": ["Biotechnology"]},
    {"name": "Biotech", "index": "XBI", "group": "Healthcare", "sub": ["Biotechnology"]},
    {"name": "Discretionary", "index": "XLY", "group": "Consumption", "sector": ["Consumer Discretionary"], "not_sub": ["Homebuilding", "Home Improvement Retail", "Homefurnishing Retail", "Home Furnishings", "Household Appliances"]},
    {"name": "Staples", "index": "XLP", "group": "Consumption", "sector": ["Consumer Staples"]},
    {"name": "Airlines", "index": "JETS", "group": "Consumption", "sub": ["Passenger Airlines"]},
    {"name": "Homebuilders", "index": "XHB", "group": "Consumption", "sub": ["Homebuilding", "Building Products", "Home Improvement Retail", "Homefurnishing Retail", "Home Furnishings", "Household Appliances"]},
    {"name": "Energy", "index": "XLE", "group": "Commodities & energy", "sector": ["Energy"], "not_sub": ["Coal & Consumable Fuels"]},
    {"name": "Materials", "index": "XLB", "group": "Commodities & energy", "sector": ["Materials"], "not_sub": ["Aluminum", "Copper", "Gold", "Silver", "Steel", "Diversified Metals & Mining"]},
    {"name": "Metals & Mining", "index": "XME", "group": "Commodities & energy", "sub": ["Aluminum", "Copper", "Gold", "Silver", "Steel", "Diversified Metals & Mining", "Coal & Consumable Fuels"]},
    {"name": "Clean Energy", "index": "ICLN", "group": "Commodities & energy", "sub": ["Renewable Electricity"],
     "symbols": ["ENPH", "FSLR", "SEDG", "RUN", "ARRY", "SHLS", "NXT", "PLUG", "BE", "FCEL", "BLDP", "CWEN", "ORA", "NOVA", "MAXN", "FLNC", "STEM", "EOSE", "ENVX", "AMPS"]},
    {"name": "Industrials", "index": "XLI", "group": "Industrials & real assets", "sector": ["Industrials"], "not_sub": ["Aerospace & Defense", "Passenger Airlines"]},
    {"name": "Defense", "index": "ITA", "group": "Industrials & real assets", "sub": ["Aerospace & Defense"]},
    {"name": "Real Estate", "index": "XLRE", "group": "Industrials & real assets", "sector": ["Real Estate"]},
    {"name": "Utilities", "index": "XLU", "group": "Industrials & real assets", "sector": ["Utilities"], "not_sub": ["Renewable Electricity"]},
]
GROUPS = ["Tech & media", "Financials", "Healthcare", "Consumption", "Commodities & energy", "Industrials & real assets"]
INDICES = {"SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI"}
BENCH = "^GSPC"

U = {"list": {}, "all": {}, "ndx": set(), "cls": {}, "hist": {}, "progress": ""}


def ysym(s):
    """Yahoo writes share classes with a dash: BRK.B -> BRK-B."""
    return s.replace(".", "-").replace("/", "-").strip().upper()


def _wiki(title):
    import re
    html = M.get(f"https://en.wikipedia.org/wiki/{title}").decode()
    t = pd.read_html(io.StringIO(html), match="GICS Sub-Industry")[0]
    return t


def _rows(df, tier):
    out = {}
    for _, r in df.iterrows():
        s = ysym(str(r["Symbol"]))
        cik = r.get("CIK")
        out[s] = {"name": str(r["Security"]), "sector": str(r["GICS Sector"]), "sub": str(r["GICS Sub-Industry"]), "tier": tier,
                  "cik": int(cik) if pd.notna(cik) and str(cik).strip() not in ("", "nan") else None}
    return out


def sp1500():
    sp = pd.read_csv(io.StringIO(M.get("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv").decode()))
    sp = sp.rename(columns={"GICS Sector": "GICS Sector"})
    out = _rows(sp, "S&P 500")
    for title, tier in (("List_of_S%26P_400_companies", "S&P 400"), ("List_of_S%26P_600_companies", "S&P 600")):
        try:
            for s, v in _rows(_wiki(title), tier).items():
                out.setdefault(s, v)
        except Exception:
            pass
    return out


def nasdaq100():
    import json as _j
    import urllib.request
    req = urllib.request.Request("https://api.nasdaq.com/api/quote/list-type/nasdaq100", headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = _j.loads(r.read())
    return sorted({ysym(x["symbol"]) for x in d["data"]["data"]["rows"]})


def all_listed():
    """Every US-listed symbol (Nasdaq, NYSE, NYSE American, Cboe): stocks and ETFs; test issues, warrants, units and rights dropped."""
    out = {}
    nasdaq = M.get("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt").decode().splitlines()
    other = M.get("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt").decode().splitlines()
    for lines, ex_col, sym_col, etf_col, test_col in ((nasdaq, 2, 0, 6, 3), (other, 2, 0, 4, 6)):
        for ln in lines[1:]:
            c = ln.split("|")
            if len(c) < 7 or ln.startswith("File Creation"):
                continue
            sym, name = c[sym_col].strip(), c[1].strip()
            if c[test_col] == "Y" or any(x in sym for x in ("$", "^")) or len(sym) > 5:
                continue
            low = name.lower()
            if any(w in low for w in (" warrant", " rights", " right ", " unit", "preferred", "depositary", "notes due", " note ", "% ")):
                continue
            out[ysym(sym)] = {"name": name.split(" - ")[0], "etf": c[etf_col] == "Y", "ex": "Nasdaq" if lines is nasdaq else {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe", "V": "IEX"}.get(c[ex_col], c[ex_col])}
    return out


YAHOO_SECTOR = {"Technology": "Information Technology", "Communication Services": "Communication Services", "Consumer Cyclical": "Consumer Discretionary",
                "Consumer Defensive": "Consumer Staples", "Healthcare": "Health Care", "Financial Services": "Financials", "Basic Materials": "Materials",
                "Industrials": "Industrials", "Energy": "Energy", "Utilities": "Utilities", "Real Estate": "Real Estate"}


YAHOO_SUB = {"Semiconductor Equipment & Materials": "Semiconductor Materials & Equipment", "Software - Application": "Application Software",
             "Software - Infrastructure": "Systems Software", "Internet Retail": "Broadline Retail", "Internet Content & Information": "Interactive Media & Services",
             "Beverages - Non-Alcoholic": "Soft Drinks & Non-alcoholic Beverages", "Engineering & Construction": "Construction & Engineering",
             "Specialty Business Services": "Diversified Support Services"}


def extras(lst, nd):
    """Nasdaq-100 members outside the S&P 1500 (foreign issuers, new listings): sector and industry from Yahoo's company profile."""
    from . import yahoo as Y
    out, t0 = {}, time.time()
    for s in nd:
        if s in lst:
            continue
        if time.time() - t0 > 40:                        # the profiles are a nicety: never hold up the whole start for them
            out[s] = {"name": s, "sector": "Other", "sub": "Other", "tier": "Nasdaq-100", "cik": None}
            continue
        try:
            r = Y.summary(s, "assetProfile,price")
            ap = r.get("assetProfile") or {}
            name = (r.get("price") or {}).get("longName") or (r.get("price") or {}).get("shortName") or s
            out[s] = {"name": name, "sector": YAHOO_SECTOR.get(ap.get("sector"), "Other"), "sub": YAHOO_SUB.get(ap.get("industry"), ap.get("industry") or "Other"), "tier": "Nasdaq-100", "cik": None}
        except Exception:
            out[s] = {"name": s, "sector": "Other", "sub": "Other", "tier": "Nasdaq-100", "cik": None}
        time.sleep(0.3)
    return out


def load_lists():
    """The lists, from disk when under a week old."""
    try:
        d = json.loads(LISTS.read_text())
        if time.time() - d["fetched"] < 7 * 86400:
            U.update(list=d["list"], all=d["all"], ndx=set(d["ndx"]))
            return
    except Exception:
        d = None
    try:
        U["progress"] = "reading the S&P 500, 400 and 600 lists"
        lst = sp1500()
        U["progress"] = "reading every US listing from Nasdaq's directory"
        al = all_listed()
        U["progress"] = "reading the Nasdaq-100"
        try:
            nd = nasdaq100()
        except Exception:
            nd = sorted(d["ndx"]) if d else []           # unreachable right now: keep the last list, or go without it
        U["progress"] = "looking up foreign Nasdaq-100 issuers"
        lst.update(extras(lst, nd))
        U["progress"] = ""
        U.update(list=lst, all=al, ndx=set(nd))
        LISTS.write_text(json.dumps({"fetched": time.time(), "list": lst, "all": al, "ndx": nd}))
    except Exception:
        if d:
            U.update(list=d["list"], all=d["all"], ndx=set(d["ndx"]))
        else:
            raise


def tape():
    """The live-tape universe (the US counterpart of the F&O list): the S&P 500 and the Nasdaq-100."""
    return sorted({s for s, v in U["list"].items() if v["tier"] == "S&P 500"} | U["ndx"])


def members(sec):
    out = []
    for s, v in U["list"].items():
        ok = s in sec.get("symbols", [])
        if not ok and "sector" in sec:
            ok = v["sector"] in sec["sector"] and v["sub"] not in sec.get("not_sub", [])
        if not ok and "sub" in sec:
            ok = v["sub"] in sec["sub"]
        if ok:
            out.append(s)
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def yahoo_daily(y, rng="1y"):
    d = M.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(y)}?interval=1d&range={rng}")["chart"]["result"][0]
    o = d["indicators"]["quote"][0]
    return pd.DataFrame({"close": o["close"], "high": o["high"], "low": o["low"], "volume": o["volume"]},
                        index=pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert(M.ET).normalize().tz_localize(None)).dropna(subset=["close"])


def build_history(log=print, workers=3):
    """A year of daily bars per S&P 1500 stock and sector ETF, stored per day so a restart does not fetch again.
    Three polite workers; a half-finished day is kept on disk and resumed."""
    from concurrent.futures import ThreadPoolExecutor
    day = M.now_et().date().isoformat()
    p, part = HIST / f"{day}.pkl", HIST / f"{day}.part.pkl"
    if p.exists():
        U["hist"] = pd.read_pickle(p)
        return
    old = sorted(HIST.glob("*.pkl"))
    old = [q for q in old if not q.name.endswith(".part.pkl")]
    if part.exists():
        saved = pd.read_pickle(part)
        hist, fresh = saved["hist"], set(saved["fresh"])
    else:
        hist, fresh = (pd.read_pickle(old[-1]) if old else {}), set()
    U["hist"] = hist
    todo = [("IDX:" + v, v) for v in INDICES.values()] + [("IDX:" + s["index"], s["index"]) for s in SECTORS] + [(s, s) for s in U["list"]]
    todo = [t for t in todo if t[0] not in fresh]
    total = len(todo) + len(fresh)
    state = {"done": 0, "pause": 0.0}

    def one(item):
        k, y = item
        for attempt in range(3):
            if state["pause"] > time.time():
                time.sleep(max(0, state["pause"] - time.time()))
            try:
                hist[k] = yahoo_daily(y)
                fresh.add(k)
                break
            except Exception as e:
                if "429" in str(e):
                    state["pause"] = time.time() + 60
                    log("Yahoo asked us to slow down; pausing 60 s")
                    continue
                break
        state["done"] += 1
        if state["done"] % 100 == 0:
            U["progress"] = f"daily history {len(fresh)}/{total}"
            log(f"US daily history {len(fresh)} done")
            pd.to_pickle({"hist": dict(hist), "fresh": sorted(fresh)}, part)
        time.sleep(0.15)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, todo))
    pd.to_pickle(hist, p)
    part.unlink(missing_ok=True)
    for q in old[:-2]:
        q.unlink(missing_ok=True)
    U["hist"] = hist
    U["progress"] = ""
    log(f"US history: {len(hist)} series")


def stats(sym):
    """Week / month / 3-month moves, 50-day average, 52-week high and normal volume from the daily bars."""
    h = U["hist"].get(sym)
    if h is None or len(h) < 25:
        return {}
    c, v = h["close"], h["volume"]
    r = lambda n: float(c.iloc[-1] / c.iloc[-1 - n] - 1) * 100 if len(c) > n else None
    return {"w1": r(5), "m1": r(21), "m3": r(63), "dma50": float(c.iloc[-50:].mean()) if len(c) >= 50 else None,
            "high52": float(h["high"].max()), "vol60": float(v.iloc[-60:].mean()) if v.iloc[-60:].mean() else None}


def sector_series(syms):
    """A sector with no ETF history: the middle stock's path, rebased to 100 over the last 70 days."""
    cols = [U["hist"][s]["close"].iloc[-70:] for s in syms if s in U["hist"] and len(U["hist"][s]) >= 70]
    if not cols:
        return None
    df = pd.concat(cols, axis=1).ffill().dropna(how="all")
    return (df / df.iloc[0]).median(axis=1) * 100
