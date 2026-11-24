"""Yahoo Finance with its cookie and crumb, which the batch quote and company-summary endpoints ask for.
One shared session; the crumb is refreshed when Yahoo says it expired."""
import http.cookiejar
import json
import threading
import time
import urllib.parse
import urllib.request

_LOCK = threading.Lock()
_S = {"op": None, "crumb": None, "t": 0}


def _open():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", "Mozilla/5.0")]
    try:
        op.open("https://fc.yahoo.com", timeout=15)       # answers 404 but sets the cookie
    except Exception:
        pass
    crumb = op.open("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=15).read().decode()
    if not crumb or "<" in crumb:
        raise RuntimeError("Yahoo gave no crumb")
    _S.update(op=op, crumb=crumb, t=time.time())


def get_json(url, timeout=20, retry=True):
    with _LOCK:
        if not _S["op"] or time.time() - _S["t"] > 6 * 3600:
            _open()
        op, crumb = _S["op"], _S["crumb"]
    sep = "&" if "?" in url else "?"
    try:
        return json.loads(op.open(f"{url}{sep}crumb={urllib.parse.quote(crumb)}", timeout=timeout).read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and retry:
            with _LOCK:
                _S["op"] = None
            return get_json(url, timeout, retry=False)
        raise


def quotes(symbols):
    """Batch quote: price, change, volume, market cap, P/E, 52-week range, 50/200-day averages. Up to ~150 per call."""
    out = {}
    for i in range(0, len(symbols), 150):
        chunk = symbols[i:i + 150]
        d = get_json("https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + urllib.parse.quote(",".join(chunk)))
        for r in d["quoteResponse"]["result"]:
            out[r["symbol"]] = r
        time.sleep(0.15)
    return out


def summary(sym, modules):
    d = get_json(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(sym)}?modules={modules}", 25)
    return (d["quoteSummary"]["result"] or [{}])[0]
