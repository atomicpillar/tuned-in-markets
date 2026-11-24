"""Updates Tuned in Markets to the latest version without touching your settings or history.
It downloads the newest copy from GitHub, replaces the program files, and leaves your .env (keys, contact), data folder
(history, watchlist, results) and private Python environment exactly as they are. Run it with update.sh (Mac) or update.bat (Windows).
Stop the app first (Ctrl+C), run this, then start the app again."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

URL = os.environ.get("TUNED_UPDATE_URL", "https://github.com/atomicpillar/tuned-in-markets/archive/refs/heads/main.zip")
ROOT = Path(__file__).resolve().parent.parent
KEEP = {".env", "data", ".venv"}            # never replaced


def main():
    print("Downloading the latest version...")
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "TunedInMarkets-updater"})
        raw = urllib.request.urlopen(req, timeout=120).read()
    except Exception as e:
        sys.exit(f"Could not download the update ({e}). Check your internet connection and try again. Nothing was changed.")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            zipfile.ZipFile(io.BytesIO(raw)).extractall(tmp)
        except zipfile.BadZipFile:
            sys.exit("The download was not a valid update file. Nothing was changed.")
        tops = [p for p in Path(tmp).iterdir() if p.is_dir()]
        if len(tops) != 1 or not (tops[0] / "app.py").exists():
            sys.exit("The download did not look like Tuned in Markets. Nothing was changed.")
        src, n = tops[0], 0
        for f in sorted(src.rglob("*")):
            if f.is_dir():
                continue
            rel = f.relative_to(src)
            if rel.parts[0] in KEEP:
                continue
            dst = ROOT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or dst.read_bytes() != f.read_bytes():
                shutil.copy2(f, dst)
                n += 1
    print(f"{n} files updated. Your .env and data folder were not touched.")
    if (ROOT / "requirements.txt").exists():
        print("Checking the libraries...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")], check=False)
    print("\nDone. Start the app again:  Mac: bash run.sh (or bash remote.sh)   Windows: run.bat")


if __name__ == "__main__":
    main()
