"""The US Strategy Lab. The swing system, the portfolio simulator and the tables are the India lab's own files,
loaded a second time under the name `lab_us` so they read the US settings in lab/mk.py (S&P 1500, S&P 500 filter,
US costs, dollars). Nothing is copied: a fix to a rule lands in both markets.

Setup (runs in the background on the first start, then weekly): five years of daily bars for the S&P 1500 from Yahoo,
the backtest of every swing strategy, and the Lab summary. Afterwards the live scan runs after each US close."""
import importlib
import importlib.util
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import market as M
from . import universe as U

LABDIR = Path(__file__).resolve().parent.parent / "lab"
STATE = {"phase": "idle", "msg": "", "ready": False}
_L = {}


def pkg():
    """The lab package for the US: same files as `lab`, loaded as `lab_us`."""
    if "lab_us" not in sys.modules:
        spec = importlib.util.spec_from_file_location("lab_us", LABDIR / "__init__.py", submodule_search_locations=[str(LABDIR)])
        mod = importlib.util.module_from_spec(spec)
        sys.modules["lab_us"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["lab_us"]


def mod(name):
    pkg()
    return importlib.import_module(f"lab_us.{name}")


def fetch_bars(syms, log=print, workers=3, fresh_hours=12):
    B = mod("bars")
    todo = [s for s in syms if not (B.path(s, "1d").exists() and time.time() - B.path(s, "1d").stat().st_mtime < fresh_hours * 3600)]
    pause = {"until": 0.0}
    done = {"n": 0}

    def one(s):
        for _ in range(3):
            if pause["until"] > time.time():
                time.sleep(pause["until"] - time.time())
            try:
                B.save(s, "1d", B.download(s, "1d"))
                break
            except Exception as e:
                if "429" in str(e):
                    pause["until"] = time.time() + 60
                    log("Yahoo asked us to slow down; pausing 60 s")
                    continue
                break
        done["n"] += 1
        if done["n"] % 100 == 0:
            STATE["msg"] = f"US daily bars {done['n']}/{len(todo)}"
            log(STATE["msg"])
        time.sleep(0.15)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, todo))


def write_classification():
    cls = {s: {"sector": c.get("sector"), "mcap": c.get("mcap"), "name": c.get("name")} for s, c in U.U["cls"].items()}
    (M.DATA / "us_classification.json").write_text(json.dumps(cls))


def setup(log=print):
    B = mod("bars")
    STATE.update(phase="download", msg="downloading five years of daily bars")
    fetch_bars(list(B.INDICES) + B.universe(), log)
    write_classification()
    STATE.update(phase="backtest", msg="running the swing backtest")
    t = mod("swing").run_all()
    log(f"US swing backtest: {len(t):,} trades")
    STATE.update(phase="summary", msg="building the summary")
    mod("swing_live").build_summary()
    STATE.update(phase="done", msg="", ready=True)


def swing_live():
    return mod("swing_live")


def run(log=print):
    """Background: set up when there is no summary yet (or it is a week old), then scan after every close."""
    out = M.DATA / "us_swing_summary.json"
    if out.exists():                                   # a summary from an earlier run: the lab is usable at once, a refresh happens in the background
        STATE.update(phase="done", ready=True)
    while not U.U["list"]:
        time.sleep(5)
    for _ in range(360 if not STATE["ready"] else 0):                               # the bulk download waits for the live tape and the price history (at most 30 minutes)
        if len(U.U["hist"]) >= 1400:
            break
        time.sleep(5)
    try:
        if not out.exists() or time.time() - out.stat().st_mtime > 7 * 86400:
            setup(log)
        else:
            STATE.update(phase="done", ready=True)
        write_classification()
        swing_live().run(log)
    except Exception as e:
        STATE.update(phase="error", msg=str(e))
        log(f"US lab: {e}")


def summary():
    if not STATE["ready"]:
        return {"error": "The US strategy lab is being built: " + (STATE["msg"] or "waiting for the universe") + ". This runs once and takes about 15 minutes.", "building": True}
    return swing_live().summary()
