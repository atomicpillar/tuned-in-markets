"""Which market this copy of the swing lab runs for. The India lab imports as `lab`; the US lab is the very same
files loaded a second time as `lab_us` (see us/lab.py), so every module reads its market's settings from here
and the rules, simulator and tables are written once."""
import json

US = __package__ == "lab_us"

if US:
    from us import market as M
    from us import universe as _U
    BARS, BENCH, TRADES, SUMMARY, CLS = "us_bars", "SPX", "us_swing_trades.pkl", "us_swing_summary.json", "us_classification.json"
    INDICES = {"SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI", "RUT": "^RUT", "VIX": "^VIX"}
    SUFFIX, TZ, VAL, MCAP = "", M.ET, 1e6, 1e6
    # round trip: slippage 0.05% a side, SEC and FINRA fees on the sell (a few thousandths of a percent); no commission
    COST = 0.001 + 0.0000278 + 0.00002
    SIZE = [(50000, "Large cap ($50B+)"), (10000, "Mid cap ($10-50B)"), (1, "Small cap (< $10B)")]
    LIQ = ([0, 20, 100, 500, 1e9], ["Turnover < $20M/day", "$20-100M/day", "$100-500M/day", "$500M+/day"])
    BENCH_NAME, RS_TITLE, RS_WEAK = "S&P 500", "Strength vs S&P 500 (3 months)", "Weaker than the S&P 500"
    CAND = {"strat": "VCP tightening break", "exit": "rr3_40", "k": 10,
            "label": "VCP tightening break · S&P 500 above 200-DMA · 3R / 40 days",
            "rules": ["Universe: S&P 1500 (large, mid and small caps), cash account, longs only",
                      "Market filter: buy only while the S&P 500 closes above its 200-day average",
                      "Stock trend: close > 200 SMA, 50 SMA > 200 SMA, 20 EMA > 50 SMA",
                      "Setup: within 8% of the 52-week high, the last 10 days' range under 3.6 × ATR (tightening)",
                      "Trigger: close above the 10-day high on volume ≥ 1.3 × the 50-day average; buy next day's open",
                      "Stop: under the 10-day low (−0.3 ATR); target 3 × risk; exit after 40 trading days at the latest",
                      "Up to 10 positions of 10% each; when several trigger, take the strongest vs the S&P 500 (63-day relative strength) first"]}

    def universe():
        return sorted(_U.U["list"])

    def now():
        return M.now_et()
    AFTER_CLOSE = 17
else:
    from sm import market as M
    BARS, BENCH, TRADES, SUMMARY, CLS = "bars", "NIFTY", "swing_trades.pkl", "swing_summary.json", "classification.json"
    INDICES = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN", "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
               "MIDCPNIFTY": "NIFTY_MID_SELECT.NS", "NIFTYIT": "^CNXIT", "NIFTYAUTO": "^CNXAUTO", "NIFTYPHARMA": "^CNXPHARMA",
               "NIFTYMETAL": "^CNXMETAL", "NIFTYFMCG": "^CNXFMCG", "NIFTYREALTY": "^CNXREALTY", "NIFTYENERGY": "^CNXENERGY",
               "NIFTYPSUBANK": "^CNXPSUBANK", "NIFTYINFRA": "^CNXINFRA", "NIFTYMIDCAP": "NIFTY_MIDCAP_100.NS", "INDIAVIX": "^INDIAVIX"}
    SUFFIX, TZ, VAL, MCAP = ".NS", M.IST, 1e7, 1e7
    COST = None                     # computed in swing.py from the Indian delivery charges
    SIZE = [(50000, "Large cap (₹50k cr+)"), (15000, "Mid cap (₹15–50k cr)"), (1, "Small cap (< ₹15k cr)")]
    LIQ = ([0, 10, 30, 100, 1e9], ["Turnover < ₹10 cr/day", "₹10–30 cr/day", "₹30–100 cr/day", "₹100 cr+/day"])
    BENCH_NAME, RS_TITLE, RS_WEAK = "Nifty 50", "Strength vs Nifty (3 months)", "Weaker than Nifty"
    CAND = None                     # defined in swing_live.py

    def universe():
        return None

    def now():
        return M.now_ist()
    AFTER_CLOSE = 16
