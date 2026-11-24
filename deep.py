"""Deep research on one stock with TradingAgents (a multi-agent LLM framework: analysts, a bull and a bear researcher,
a trader and a risk team debate and produce a decision with reasons). It is the slow, paid second stage: Tuned in Markets
scans and flags, you click a stock, this runs. It uses YOUR LLM key, runs on your computer, and is research, not advice.

TradingAgents lives in its own folder and Python environment (see docs/DEEP-RESEARCH.md); this file starts it as a
subprocess so its libraries never clash with Tuned in Markets's, and keeps one result per stock per day."""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

from sm import market as SM
from us import market as USM

ROOT = Path(__file__).resolve().parent
OUT = SM.DATA / "deep"
OUT.mkdir(exist_ok=True)
RUNS = {}
LOCK = threading.Lock()


def python():
    """The Python of the TradingAgents environment: TRADINGAGENTS_PYTHON, or the one the setup script made."""
    for p in (os.environ.get("TRADINGAGENTS_PYTHON"), Path.home() / "tradingagents" / ".venv" / "bin" / "python",
              Path.home() / "tradingagents" / ".venv" / "Scripts" / "python.exe"):
        if p and Path(p).exists():
            return str(p)
    return None


def llm_ready():
    return any(os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "XAI_API_KEY"))


def ticker(mk, sym):
    """Yahoo-style ticker, which TradingAgents resolves per market: RELIANCE.NS in India, plain AAPL / BRK-B in the US."""
    sym = sym.upper().replace(".", "-") if mk == "US" else sym.upper()
    return sym if mk == "US" or sym.startswith("^") else sym + ".NS"


def trade_date(mk):
    d = USM.last_session() if mk == "US" else SM.now_ist().date()
    if mk == "IN":
        hol = SM.holidays()
        while not SM.is_trading_day(d, hol):
            d -= timedelta(days=1)
    return d.isoformat()


def _file(mk, sym, date):
    return OUT / f"{mk}-{sym.upper().replace('/', '_')}-{date}.json"


def status(mk, sym):
    date = trade_date(mk)
    f = _file(mk, sym, date)
    if f.exists():
        r = json.loads(f.read_text())
        return {"state": "done" if r.get("ok") else "error", **r, "built": int(f.stat().st_mtime)}
    run = RUNS.get((mk, sym.upper()))
    if run and run["proc"].poll() is None:
        return {"state": "running", "elapsed": int(time.time() - run["t"]), "date": date}
    if not python():
        return {"state": "setup", "why": "TradingAgents is not installed yet."}
    if not llm_ready():
        return {"state": "setup", "why": "No LLM key found in .env (ANTHROPIC_API_KEY, OPENAI_API_KEY or GOOGLE_API_KEY)."}
    return {"state": "none", "date": date}


def start(mk, sym):
    st = status(mk, sym)
    if st["state"] != "none":
        return st
    date = trade_date(mk)
    with LOCK:
        proc = subprocess.Popen([python(), str(ROOT / "tools" / "deep_research.py"), ticker(mk, sym), date, str(_file(mk, sym, date))],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(os.environ))
        RUNS[(mk, sym.upper())] = {"proc": proc, "t": time.time()}
    return {"state": "running", "elapsed": 0, "date": date}
