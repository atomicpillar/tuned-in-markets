"""Reads KEY=VALUE lines from a `.env` file next to the app into the environment (never overriding a variable that is
already set). Keys for Alpaca and for the LLM that TradingAgents uses live there; `.env` is git-ignored."""
import os
from pathlib import Path


def load(path=None):
    p = Path(path or Path(__file__).resolve().parent / ".env")
    if not p.exists():
        return 0
    n = 0
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
            n += 1
    return n


def save(key, value, path=None):
    """Write one KEY=VALUE into `.env` (created if missing) and into the running process."""
    p = Path(path or Path(__file__).resolve().parent / ".env")
    lines = p.read_text().splitlines() if p.exists() else []
    out, done = [], False
    for ln in lines:
        if ln.split("=", 1)[0].strip() == key and not ln.strip().startswith("#"):
            out.append(f"{key}={value}"); done = True
        else:
            out.append(ln)
    if not done:
        out.append(f"{key}={value}")
    p.write_text("\n".join(out) + "\n")
    os.environ[key] = value


def sec_user_agent():
    """SEC asks every automated client to name itself and give a contact. Each user supplies their own (SEC_CONTACT_NAME, SEC_CONTACT_EMAIL)."""
    name, mail = os.environ.get("SEC_CONTACT_NAME", "").strip(), os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if name and mail:
        return f"TunedInMarkets personal-use research ({name} {mail})"
    return "TunedInMarkets personal-use research app"


def sec_ready():
    return bool(os.environ.get("SEC_CONTACT_NAME", "").strip() and "@" in os.environ.get("SEC_CONTACT_EMAIL", ""))


def sec_headers():
    return {"User-Agent": sec_user_agent(), "Accept-Encoding": "identity"}
