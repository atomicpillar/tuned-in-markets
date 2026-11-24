"""Earnings, dividends, ownership and insider activity for the long-term view.

US insider trades are read from the company's own Form 4 filings on SEC EDGAR (official). Only open-market buys (code P) and
sales (code S) are counted as the insiders' own decisions: grants, option exercises and tax withholding are listed apart, because
they are pay, not a view. Holder percentages and earnings history come from Yahoo; India's promoter and public holding by
quarter comes from NSE's shareholding filings."""
import envfile
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

from us import market as M
from us import research as R
from us import yahoo as Y

CODES = {"P": "open-market buy", "S": "open-market sale", "A": "grant or award", "M": "option exercise", "F": "tax withholding", "G": "gift", "D": "returned to company", "C": "conversion"}


def _raw(d, k):
    v = (d or {}).get(k)
    return v.get("raw") if isinstance(v, dict) else v


def _day(ts):
    try:
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if ts else None
    except Exception:
        return None


def events(mk, sym, y):
    out = {"source": "Yahoo Finance", "next_earnings": None, "earnings": [], "dividend": None}
    try:
        r = Y.summary(y, "calendarEvents,earningsHistory,summaryDetail")
    except Exception as e:
        out["error"] = f"Yahoo summary unavailable ({type(e).__name__})"
        return out
    ce = r.get("calendarEvents") or {}
    ed = (ce.get("earnings") or {}).get("earningsDate") or []
    nxt = [_day(_raw(x, "raw") if isinstance(x, dict) and "raw" in x else x.get("raw") if isinstance(x, dict) else None) for x in ed]
    nxt = [d for d in nxt if d and d >= date.today().isoformat()]
    out["next_earnings"] = nxt[0] if nxt else None
    for h in (r.get("earningsHistory") or {}).get("history") or []:
        out["earnings"].append({"quarter": _day(_raw(h, "quarter")), "actual": _raw(h, "epsActual"), "estimate": _raw(h, "epsEstimate"),
                                "surprise_pct": None if _raw(h, "surprisePercent") is None else round(_raw(h, "surprisePercent") * 100, 1)})
    sd = r.get("summaryDetail") or {}
    if _raw(sd, "dividendRate") or _raw(sd, "trailingAnnualDividendRate"):
        out["dividend"] = {"yield": None if _raw(sd, "dividendYield") is None else round(_raw(sd, "dividendYield") * 100, 2), "rate": _raw(sd, "dividendRate") or _raw(sd, "trailingAnnualDividendRate"),
                           "ex_date": _day(_raw(sd, "exDividendDate")), "payout": None if _raw(sd, "payoutRatio") is None else round(_raw(sd, "payoutRatio") * 100)}
    return out


def _form4(cik, acc, doc):
    """The non-derivative transactions of one Form 4, parsed from the filing's own XML."""
    xml = urllib.request.urlopen(urllib.request.Request(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc.split('/')[-1]}", headers=envfile.sec_headers()), timeout=30).read()
    root = ET.fromstring(xml)
    g = lambda node, path: (node.findtext(path) or "").strip()
    owner = g(root, "reportingOwner/reportingOwnerId/rptOwnerName")
    rel = root.find("reportingOwner/reportingOwnerRelationship")
    title = g(rel, "officerTitle") if rel is not None else ""
    if rel is not None and not title:
        title = "Director" if g(rel, "isDirector") in ("1", "true") else "10% owner" if g(rel, "isTenPercentOwner") in ("1", "true") else ""
    out = []
    for t in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        try:
            sh = float(g(t, "transactionAmounts/transactionShares/value") or 0)
            px = float(g(t, "transactionAmounts/transactionPricePerShare/value") or 0)
        except ValueError:
            continue
        out.append({"date": g(t, "transactionDate/value")[:10], "code": g(t, "transactionCoding/transactionCode"), "shares": sh, "price": px,
                    "side": g(t, "transactionAmounts/transactionAcquiredDisposedCode/value"), "owner": owner, "title": title})
    return out


def insiders_us(sym, days=180, limit=40):
    """Insider trades from SEC Form 4 filings over the last `days`: counts and dollars of open-market buys and sales, and the list."""
    cik = R.cik_of(sym)
    if not cik:
        return None
    sub = R._sec(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    rec = sub["filings"]["recent"]
    cut = (date.today() - timedelta(days=days)).isoformat()
    forms = [(rec["filingDate"][i], rec["accessionNumber"][i], rec["primaryDocument"][i]) for i in range(len(rec["form"])) if rec["form"][i] == "4" and rec["filingDate"][i] >= cut][:limit]
    trades = []
    for fd, acc, doc in forms:
        try:
            trades += [{**t, "filed": fd} for t in _form4(cik, acc, doc)]
        except Exception:
            pass
        time.sleep(0.12)
    mk_ = [t for t in trades if t["code"] in ("P", "S") and t["shares"] > 0]
    buys, sells = [t for t in mk_ if t["code"] == "P"], [t for t in mk_ if t["code"] == "S"]
    val = lambda xs: round(sum(t["shares"] * t["price"] for t in xs) / 1e6, 2)
    return {"days": days, "filings": len(forms), "buys": {"n": len(buys), "people": len({t["owner"] for t in buys}), "shares": round(sum(t["shares"] for t in buys)), "value_m": val(buys)},
            "sells": {"n": len(sells), "people": len({t["owner"] for t in sells}), "shares": round(sum(t["shares"] for t in sells)), "value_m": val(sells)},
            "recent": [{**t, "what": CODES.get(t["code"], t["code"])} for t in sorted(mk_, key=lambda t: t["date"], reverse=True)[:14]],
            "other": len([t for t in trades if t["code"] not in ("P", "S")]), "source": "SEC EDGAR Form 4 filings"}


def holders_yahoo(y):
    try:
        r = Y.summary(y, "majorHoldersBreakdown,institutionOwnership")
    except Exception:
        return None
    mh = r.get("majorHoldersBreakdown") or {}
    top = [{"name": h.get("organization"), "pct": None if _raw(h, "pctHeld") is None else round(_raw(h, "pctHeld") * 100, 2), "shares": _raw(h, "position"), "date": _day(_raw(h, "reportDate"))}
           for h in (r.get("institutionOwnership") or {}).get("ownershipList", [])[:10]]
    return {"insiders_pct": None if _raw(mh, "insidersPercentHeld") is None else round(_raw(mh, "insidersPercentHeld") * 100, 1),
            "institutions_pct": None if _raw(mh, "institutionsPercentHeld") is None else round(_raw(mh, "institutionsPercentHeld") * 100, 1),
            "institutions_count": _raw(mh, "institutionsCount"), "top": top, "source": "Yahoo Finance (from regulatory holder filings)"}


def shareholding_nse(sym):
    """Promoter and public holding by quarter from NSE's shareholding-pattern filings."""
    d = M.get_json(f"https://www.nseindia.com/api/corporate-share-holdings-master?index=equities&symbol={sym}", 20)
    rows = []
    for x in d[:12]:
        try:
            rows.append({"date": datetime.strptime(x["date"], "%d-%b-%Y").strftime("%Y-%m-%d"), "promoter": float(x["pr_and_prgrp"]), "public": float(x["public_val"])})
        except Exception:
            pass
    return sorted(rows, key=lambda r: r["date"])


def ownership(mk, sym, y):
    out = {"holders": holders_yahoo(y)}
    if mk == "US":
        try:
            out["insider_trades"] = insiders_us(sym)
        except Exception as e:
            out["insider_trades_error"] = f"SEC filings unavailable ({type(e).__name__})"
    else:
        try:
            out["shareholding"] = {"rows": shareholding_nse(sym), "source": "NSE shareholding pattern filings"}
        except Exception as e:
            out["shareholding_error"] = f"NSE shareholding unavailable ({type(e).__name__})"
    return out
