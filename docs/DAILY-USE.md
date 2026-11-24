# Using it day to day

## How long until it is ready

When you start the app, prices begin to flow within about a minute. Everything else is built in the background and appears as it finishes.

| Moment | How long | What happens |
|---|---|---|
| Very first run | 30 to 40 min | Five years of history, the Swing Lab backtest, the screeners |
| A normal restart | 12 to 20 min | Price history for each market, scans, breadth, the sector map settle |
| App already running | none | Open the page |

**Active traders:** start it 20 minutes before the open, or leave it running all day and night. Restarting during the session means a few minutes of partial data.

The orange **Warming up** note in the top bar disappears when the app has finished loading. Click the orange notice in the middle of the bar to see each feed's status: how old the live prices are, how many stocks have history, whether the Swing Lab is ready.

## What refreshes, and how often

| Data | Refresh |
|---|---|
| Live prices, the clock, the last candle on a chart | every 3 to 15 seconds |
| Breadth and market health | every 45 seconds while the market is open |
| News | every 10 minutes |
| Alerts, setups, signals | as they occur, and after every close |
| Fundamentals and long-term scores | daily |
| Swing Lab backtest | weekly |

Prices come from Yahoo. US prices typically trail the exchange by about 10 to 20 seconds and Indian stocks by a few seconds. Some indices, such as the Sensex, are 15 minutes late; the page labels them.

## Keep the computer awake

The app only works while your computer is awake and the window is open.
- **Mac:** `bash remote.sh` keeps the Mac awake while it runs. With the normal `bash run.sh`, use System Settings, Battery or Energy, and stop the Mac from sleeping on power.
- **Windows:** Settings, System, Power, and set "Screen and sleep" to **Never** while plugged in.

## Open it from your phone or another computer (free, private)

Tailscale is a free private network between your own devices. Nothing is exposed to the internet.

1. Install **Tailscale** on the computer running the app and on the phone or laptop, from https://tailscale.com/download. Sign in to the same account on both.
2. On the computer running the app, start it with:
   - Mac: `bash remote.sh`
   - Windows: double-click `remote.bat`
   It prints an address that starts with `http://100.`.
3. On the other device, with Tailscale switched on, type that address, starting with `http://`, into the browser.

Only devices signed in to your Tailscale account can reach it.
