"""Captures the README screenshots from your own running copy (so they show your real data).
    pip install playwright && playwright install chromium     # once
    python tools/screenshots.py [--market US|IN] [--deep NVDA] [--out docs/img]
Open the app first and let it warm up (see docs/DAILY-USE.md)."""
import argparse
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Run: pip install playwright && playwright install chromium")

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://localhost:8810")
ap.add_argument("--market", default="US", choices=["US", "IN"])
ap.add_argument("--deep", default="", help="a symbol you already ran deep research on, to capture the report")
ap.add_argument("--out", default="docs/img")
ap.add_argument("--exe", default="", help="path to a Chrome/Chromium binary if Playwright's own is not installed")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
m = a.market.lower()


def shot(page, name, selector=None, **kw):
    path = out / f"{m}-{name}.jpg"
    if selector:
        el = page.locator(selector).first
        el.scroll_into_view_if_needed(); page.wait_for_timeout(500)
        el.screenshot(path=path, type="jpeg", quality=88)
    else:
        page.screenshot(path=path, type="jpeg", quality=88, **kw)
    print("saved", path)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=a.exe or None)
    pg = b.new_page(viewport={"width": 1480, "height": 900}, device_scale_factor=1.5)
    pg.goto(f"{a.base}/?m={a.market}"); pg.wait_for_timeout(12000)
    # the sections live in shadow roots: find them by their host ids
    pg.add_style_tag(content="#mkt{visibility:hidden}")     # the sticky top bar would sit across the middle of each section shot
    for host, name in (("smart-host", "smart-money"), ("sector-host", "sector-map"), ("scan-host", "market-health"), ("long-host", "long-term"), ("lab-host", "swing-lab")):
        el = pg.locator(f"#{host}")
        el.scroll_into_view_if_needed(); pg.wait_for_timeout(1500)
        el.screenshot(path=out / f"{m}-{name}.jpg", type="jpeg", quality=88)
        print("saved", out / f"{m}-{name}.jpg")
    pg.evaluate("window.scrollTo(0,0)")
    pg.add_style_tag(content="#mkt{visibility:visible!important}")
    pg.click("#disc"); pg.wait_for_timeout(600)
    pg.screenshot(path=out / f"{m}-notice.jpg", type="jpeg", quality=88); print("saved notice")
    pg.keyboard.press("Escape")
    # a stock chart with its trades and the research note
    sym = a.deep or ("NVDA" if a.market == "US" else "RELIANCE")
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(500)
    pg.evaluate(f"window.openChart && window.openChart('{sym}')"); pg.wait_for_timeout(9000)
    pg.screenshot(path=out / f"{m}-chart.jpg", type="jpeg", quality=88); print("saved chart")
    if a.deep:
        pg.mouse.wheel(0, 99999); pg.wait_for_timeout(1500)
        pg.screenshot(path=out / f"{m}-deep-research.jpg", type="jpeg", quality=88); print("saved deep research")
    b.close()

try:                                                    # keep the README light: 1700 px wide, tall sections cropped
    from PIL import Image
    for f in out.glob(f"{m}-*.jpg"):
        im = Image.open(f).convert("RGB")
        im = im.crop((0, 0, im.width, min(im.height, int(im.width * 0.9))))
        im = im.resize((1700, int(im.height * 1700 / im.width)), Image.LANCZOS)
        im.save(f, quality=82, optimize=True)
except ImportError:
    pass
