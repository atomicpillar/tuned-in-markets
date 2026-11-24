"""India-only market data that Indian traders watch daily, straight from NSE's public pages (they answer from a home connection):
  - FII and DII cash-market buying and selling for the latest session (₹ crore)
  - bulk, block and short deals reported by the exchange
  - the option chain of an index or an F&O stock: put/call ratio, max pain, and the strikes with the most open interest
Figures are NSE's as published (the flows are provisional until NSE finalises them); nothing is estimated."""
import json
import time
from datetime import date, datetime

from sm import market as M

_C = {}
INDICES = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}


def _cached(key, secs, fn):
    if key in _C and time.time() - _C[key][0] < secs:
        return _C[key][1]
    v = fn()
    _C[key] = (time.time(), v)
    return v


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


HIST = M.DATA / "fii_dii.json"


def fii_dii():
    """The latest session's FII and DII cash flows, and the last ten sessions this dashboard has recorded (NSE publishes one day at a time)."""
    def go():
        rows = M.get_json("https://www.nseindia.com/api/fiidiiTradeReact", 25)
        out = {}
        for r in rows:
            k = "fii" if "FII" in r["category"].upper() or "FPI" in r["category"].upper() else "dii"
            out[k] = {"buy": _f(r["buyValue"]), "sell": _f(r["sellValue"]), "net": _f(r["netValue"]), "name": r["category"]}
            out["date"] = r["date"]
        try:
            h = json.loads(HIST.read_text())
        except Exception:
            h = {}
        try:
            h[datetime.strptime(out["date"], "%d-%b-%Y").date().isoformat()] = {"fii": out["fii"]["net"], "dii": out["dii"]["net"]}
            HIST.write_text(json.dumps(dict(sorted(h.items())[-250:])))
        except Exception:
            pass
        out["history"] = [{"date": k, **v} for k, v in sorted(h.items())[-10:]]
        return out
    return _cached("fiidii", 600, go)


def deals(symbol=None, limit=30):
    """Today's bulk, block and short deals (value in ₹ crore), biggest first, or only one symbol's."""
    def go():
        return M.get_json("https://www.nseindia.com/api/snapshot-capital-market-largedeal", 30)
    d = _cached("deals", 300, go)
    out = []
    for kind, key in (("Bulk", "BULK_DEALS_DATA"), ("Block", "BLOCK_DEALS_DATA"), ("Short", "SHORT_DEALS_DATA")):
        for r in d.get(key) or []:
            q, p = _f(r.get("qty")), _f(r.get("watp"))
            out.append({"kind": kind, "symbol": r.get("symbol"), "name": r.get("name"), "side": r.get("buySell"), "client": r.get("clientName"), "qty": q, "price": p,
                        "value_cr": round(q * p / 1e7, 2) if q and p else None})
    if symbol:
        out = [x for x in out if x["symbol"] == symbol.upper()]
    out.sort(key=lambda x: -(x["value_cr"] or 0))
    return {"as_on": d.get("as_on_date"), "deals": out[:limit], "count": len(out), "source": "NSE bulk, block and short deals"}


def option_chain(symbol):
    """PCR, max pain and the open-interest walls for the nearest expiry. Returns {'error': ...} when the symbol has no options."""
    symbol = symbol.upper()

    def go():
        info = M.get_json(f"https://www.nseindia.com/api/option-chain-contract-info?symbol={symbol}", 25)
        today = date.today()
        exps = [e for e in info.get("expiryDates", []) if datetime.strptime(e, "%d-%b-%Y").date() >= today]
        if not exps:
            return {"error": "no options for this symbol"}
        typ = "Indices" if symbol in INDICES else "Equity"
        d = M.get_json(f"https://www.nseindia.com/api/option-chain-v3?type={typ}&symbol={symbol}&expiry={exps[0]}", 40)
        rec = d.get("records") or {}
        rows = [r for r in rec.get("data", []) if r.get("expiryDates") == exps[0] and (r.get("CE") or r.get("PE"))]
        if not rows:
            return {"error": "no option chain data right now"}
        under = rec.get("underlyingValue")
        strikes = sorted({r.get("strikePrice") or (r.get("CE") or r.get("PE")).get("strikePrice") for r in rows})
        ce = {(r.get("CE") or {}).get("strikePrice"): r["CE"] for r in rows if r.get("CE")}
        pe = {(r.get("PE") or {}).get("strikePrice"): r["PE"] for r in rows if r.get("PE")}
        coi = {k: (v.get("openInterest") or 0) for k, v in ce.items()}
        poi = {k: (v.get("openInterest") or 0) for k, v in pe.items()}
        tc, tp = sum(coi.values()), sum(poi.values())
        if not tc and not tp:
            return {"error": "no open interest reported yet"}
        # max pain: the settlement price at which option buyers lose the most (sellers pay out the least)
        pain = {K: sum(c * max(0, K - s) for s, c in coi.items()) + sum(p * max(0, s - K) for s, p in poi.items()) for K in strikes}
        mp = min(pain, key=pain.get)
        atm = min(strikes, key=lambda s: abs(s - under)) if under else None
        near = [s for s in strikes if atm and abs(strikes.index(s) - strikes.index(atm)) <= 10]
        top = lambda oi, n=3: sorted(oi, key=lambda s: -oi[s])[:n]
        dc = sum((v.get("changeinOpenInterest") or 0) for v in ce.values()); dp = sum((v.get("changeinOpenInterest") or 0) for v in pe.values())
        return {"symbol": symbol, "expiry": exps[0], "underlying": under, "time": rec.get("timestamp"), "atm": atm, "pcr": round(tp / tc, 2) if tc else None,
                "call_oi": tc, "put_oi": tp, "call_oi_change": dc, "put_oi_change": dp, "max_pain": mp,
                "call_walls": [{"strike": s, "oi": coi[s]} for s in top(coi)], "put_walls": [{"strike": s, "oi": poi[s]} for s in top(poi)],
                "ladder": [{"strike": s, "call_oi": coi.get(s, 0), "put_oi": poi.get(s, 0)} for s in near],
                "atm_iv": ((ce.get(atm) or {}).get("impliedVolatility"), (pe.get(atm) or {}).get("impliedVolatility")), "source": "NSE option chain"}
    try:
        return _cached(("opt", symbol), 120, go)
    except Exception as e:
        return {"error": f"NSE option chain unavailable ({type(e).__name__})"}
