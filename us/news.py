"""Headlines for a US sector or stock (Google News, US edition), tagged as results, policy or news,
cached for 15 minutes per query. Same shape as sx/news.py."""
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from . import market as M

_CACHE = {}
RESULTS = re.compile(r"\b(q[1-4]|quarter|results?|profit|earnings|revenue|ebitda|net income|guidance|eps|fy2\d)\b", re.I)
POLICY = re.compile(r"\b(fed|fomc|sec|ftc|doj|congress|senate|white house|tariffs?|trade war|regulat\w*|antitrust|subsid\w*|sanctions?|ban|treasury|rate cuts?|rate hikes?|cpi|jobs report|budget|fda|cms)\b", re.I)
QUERY = {"Tech": "technology stocks OR apple OR microsoft OR nvidia", "Semis": "semiconductor stocks OR nvidia OR AMD OR TSMC OR chip stocks",
         "Software": "software stocks OR salesforce OR oracle OR palantir", "Comm Services": "communication services stocks OR alphabet OR meta OR netflix",
         "Financials": "bank stocks OR JPMorgan OR goldman sachs OR financial stocks", "Reg Banks": "regional bank stocks OR KRE",
         "Health Care": "healthcare stocks OR UnitedHealth OR eli lilly OR pharma", "Biotech": "biotech stocks OR FDA approval OR XBI",
         "Discretionary": "consumer discretionary stocks OR amazon OR tesla OR retail sales", "Staples": "consumer staples stocks OR walmart OR costco OR procter",
         "Airlines": "airline stocks OR delta OR united airlines", "Homebuilders": "homebuilder stocks OR mortgage rates OR housing starts",
         "Energy": "energy stocks OR exxon OR chevron OR oil prices", "Materials": "materials stocks OR chemicals OR linde",
         "Metals & Mining": "mining stocks OR freeport OR newmont OR steel prices", "Clean Energy": "clean energy stocks OR solar stocks OR first solar",
         "Industrials": "industrial stocks OR caterpillar OR boeing OR honeywell", "Defense": "defense stocks OR lockheed OR raytheon OR northrop",
         "Real Estate": "REIT stocks OR real estate stocks", "Utilities": "utility stocks OR nextera OR duke energy OR power demand data centers"}


def tag(title):
    return "RESULTS" if RESULTS.search(title) else "POLICY" if POLICY.search(title) else "NEWS"


def search(q, days=30, limit=20):
    key = (q, days)
    if key in _CACHE and time.time() - _CACHE[key][0] < 900:
        return _CACHE[key][1]
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(f"{q} when:{days}d") + "&hl=en-US&gl=US&ceid=US:en"
    try:
        root = ET.fromstring(M.get(url))
    except Exception:
        return _CACHE.get(key, (0, []))[1]
    out, seen, cutoff = [], set(), datetime.now(timezone.utc) - timedelta(days=days)
    for it in root.iter("item"):
        src, title = it.findtext("source", ""), it.findtext("title", "")
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3]
        k = title.lower()[:60]
        if k in seen:
            continue
        seen.add(k)
        try:
            t = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            continue
        if t < cutoff:
            continue
        out.append({"time": t.isoformat(), "title": title, "source": src, "link": it.findtext("link", ""), "tag": tag(title)})
    out.sort(key=lambda x: x["time"], reverse=True)
    _CACHE[key] = (time.time(), out[:limit])
    return out[:limit]


def sector(name, wait=True):
    q = QUERY.get(name, name + " stocks")
    if not wait:
        return _CACHE.get((q, 30), (0, []))[1]
    return search(q)


def warm(names):
    for n in names:
        sector(n)
        time.sleep(0.5)
    market()


def stock(sym, company):
    short = re.sub(r"\b(inc\.?|incorporated|corporation|corp\.?|company|co\.?|ltd\.?|plc|holdings|group|class [a-c])\b", "", company or sym, flags=re.I).strip(" .,")
    return search(f'"{short}" stock OR {sym}', days=60, limit=12)


def market():
    return search("\"stock market\" OR S&P 500 OR Nasdaq OR Dow Jones", days=30, limit=30)
