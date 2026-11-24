"""US long-term fundamentals straight from the SEC's XBRL filings (EDGAR): up to eleven fiscal years and twenty quarters per
company. Nothing here is estimated: every figure is a value a company reported in a 10-K or 10-Q. Money is in $ million.

Each period keeps two values: the latest one (what the company states today, restated if it later changed) for the charts,
and the first one filed with the date it was filed, so a valuation history can use only what was public on each day."""
import json
import time
from datetime import date

import pandas as pd

from us import research as R

REV = ["RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenues", "SalesRevenueNet",
       "RevenuesNetOfInterestExpense", "InterestAndDividendIncomeOperating"]
TAGS = {
    "revenue": (REV, "USD"), "gross": (["GrossProfit"], "USD"), "opinc": (["OperatingIncomeLoss"], "USD"),
    "net": (["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"], "USD"),
    "ocf": (["NetCashProvidedByUsedInOperatingActivities"], "USD"),
    "capex": (["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"], "USD"),
    "div": (["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"], "USD"),
    "shares": (["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"], "shares"),
    "eps": (["EarningsPerShareDiluted", "EarningsPerShareBasic"], "USD/shares"),
}
INST = {"equity": (["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "USD"),
        "debt": (["LongTermDebt", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", "LongTermDebtNoncurrent"], "USD"),
        "cash": (["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"], "USD"),
        "assets": (["Assets"], "USD"), "cur_assets": (["AssetsCurrent"], "USD"), "cur_liab": (["LiabilitiesCurrent"], "USD")}


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _flow(facts_list, tags, unit):
    """{(start, end): {val, val0, filed0}} merged over tags (first tag wins) and filers (newest filer wins)."""
    out = {}
    for facts in facts_list:
        for tag in tags:
            rows = (((facts.get("us-gaap") or {}).get(tag) or {}).get("units") or {}).get(unit) or []
            per = {}
            for r in rows:
                if "start" in r:
                    per.setdefault((r["start"], r["end"]), []).append(r)
            for k, rs in per.items():
                if k in out:
                    continue
                rs.sort(key=lambda r: r["filed"])
                out[k] = {"val": rs[-1]["val"], "val0": rs[0]["val"], "filed0": rs[0]["filed"], "filed": rs[-1]["filed"]}
    return out


def _instant(facts_list, tags, unit):
    out = {}
    for facts in facts_list:
        for tag in tags:
            rows = (((facts.get("us-gaap") or {}).get(tag) or {}).get("units") or {}).get(unit) or []
            per = {}
            for r in rows:
                if "start" not in r:
                    per.setdefault(r["end"], []).append(r)
            for e, rs in per.items():
                if e in out:
                    continue
                rs.sort(key=lambda r: r["filed"])
                out[e] = {"val": rs[-1]["val"], "val0": rs[0]["val"], "filed0": rs[0]["filed"]}
    return out


def _split(flow, additive=True):
    """Annual and discrete quarterly values; the fourth quarter is the year minus the other three (only for amounts that add up)."""
    ann = {e: v for (s, e), v in flow.items() if 350 <= _days(s, e) <= 380}
    qs = {e: v for (s, e), v in flow.items() if 80 <= _days(s, e) <= 100}
    for (s, e), v in flow.items():
        if additive and 350 <= _days(s, e) <= 380 and e not in qs:
            inside = sorted(x for x in qs if s < x < e and _days(s, x) < 300)
            if len(inside) >= 3:
                three = inside[-3:]
                qs[e] = {"val": v["val"] - sum(qs[x]["val"] for x in three), "val0": v["val0"] - sum(qs[x]["val0"] for x in three), "filed0": v["filed0"], "filed": v["filed"]}
    return ann, qs


def _near(d, e, tol=8):
    """The value whose date is within a week of e (52 / 53 week years drift)."""
    best, bd = None, tol + 1
    for k, v in d.items():
        x = abs(_days(k, e))
        if x < bd:
            best, bd = v, x
    return best


def load(sym):
    cik = R.cik_of(sym)
    if not cik:
        return None
    sets = [R._facts(cik)]
    if int(cik) in R.PREDECESSOR:
        sets.append(R._facts(R.PREDECESSOR[int(cik)]))
    return sets


def fundamentals(sym):
    """{annual: [...], quarterly: [...], eps_q: [...], name} in $ million, or None when the company has no XBRL filings."""
    sets = load(sym)
    if not sets:
        return None
    flows = {k: _flow(sets, t, u) for k, (t, u) in TAGS.items()}
    splits = {k: _split(f, k != "shares") for k, f in flows.items()}
    inst = {k: _instant(sets, t, u) for k, (t, u) in INST.items()}
    a_rev, q_rev = splits["revenue"]
    a_net, q_net = splits["net"]
    ends = sorted(set(a_rev) | set(a_net))
    ends = [e for e in ends if e >= "2009-01-01"][-11:]
    M = 1e6

    def pick(name, e, annual=True, scale=M):
        d = splits[name][0 if annual else 1]
        v = d.get(e) or _near(d, e)
        return v["val"] / scale if v and v["val"] is not None else None
    def filed_of(name, e, annual=True):
        d = splits[name][0 if annual else 1]
        v = d.get(e) or _near(d, e)
        return v.get("filed") if v else None
    annual = []
    for e in ends:
        row = {"end": e, "fy": e[:4]}
        for k in ("revenue", "gross", "opinc", "net", "ocf", "capex", "div"):
            row[k] = pick(k, e)
        row["shares"] = pick("shares", e, scale=1e6)
        row["eps"] = pick("eps", e, scale=1)
        row["shares_f"], row["eps_f"] = filed_of("shares", e, True), filed_of("eps", e, True)
        for k in ("equity", "debt", "cash", "assets", "cur_assets", "cur_liab"):
            v = _near(inst[k], e)
            row[k] = v["val"] / M if v else None
        row["fcf"] = row["ocf"] - row["capex"] if row["ocf"] is not None and row["capex"] is not None else None
        annual.append(row)
    qends = sorted(set(q_rev) | set(q_net) | set(splits["eps"][1]))[-20:]
    quarterly = []
    for e in qends:
        quarterly.append({"end": e, "revenue": pick("revenue", e, False), "net": pick("net", e, False), "opinc": pick("opinc", e, False),
                          "eps": pick("eps", e, False, 1), "shares": pick("shares", e, False, 1e6),
                          "shares_f": filed_of("shares", e, False), "eps_f": filed_of("eps", e, False)})
    # first-filed quarterly eps / revenue / shares with the day each became public (for the valuation history)
    pit = []
    for e in sorted(set(splits["eps"][1]) | set(q_rev)):
        r, ep, sh = q_rev.get(e), splits["eps"][1].get(e), splits["shares"][1].get(e)
        filed = (ep or r or {}).get("filed0")
        if filed:
            pit.append({"end": e, "filed": filed, "eps": ep["val0"] if ep else None, "revenue": r["val0"] / M if r else None, "shares": sh["val0"] / 1e6 if sh else None})
    return {"annual": annual, "quarterly": quarterly, "pit": pit}
