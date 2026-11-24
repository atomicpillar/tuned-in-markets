# How to read Tuned in Markets

What each number, tag and colour means, taken from how the dashboard computes it. Nothing here is a recommendation: these are rules-based readings of public prices and filings. Use it to look, question and learn.

## 1. Smart Money (the live tape)
**The big picture.** Every F&O stock in India, or every S&P 500 and Nasdaq-100 stock in the US, drawn as a line of its move since the open. Green above zero, red below.
- **Displacement:** the move since the open divided by that stock's normal daily range (the average of the last 20 days' high minus low, as a percent of price). +1 means it has already moved a typical full day, up. +2 or more is a big day for that stock. The dots under a ticker are its strength: 1 dot up to 0.8 normal days, 2 dots up to 1.6, then 3, 4, and 5 above 3.2.
- **Tiles:** the 20 strongest and 20 weakest stocks by displacement, ranked. The brackets on the waterfall mark exactly those 40. The waterfall shows every stock's current displacement, strongest at the top.
- **BOS (break of structure):** a close beyond the last confirmed swing high or low, in the direction the trend was already going. It says the trend is continuing.
- **CHoCH (change of character):** the same kind of break but against the running trend. It is the first sign a move may be turning, not proof. The tag shows the time of the break.
- **Swing high or low:** a high higher than the two bars on each side of it (and the mirror for lows), confirmed two bars later, so it is always a little late.
- **Order block (OB):** the last opposite-coloured candle before the move that broke structure, taken as where big orders went in. It is "tested" when price comes back into it and "broken" when a candle closes through it. The tile shows the nearest unbroken one and how far away it is.
- **Fair value gap (FVG):** a three-candle gap, the low of one candle above the high of the candle two before (bullish) or the reverse (bearish). Status: untouched, touched but not filled, filled.
- **Liquidity, PDH and PDL:** yesterday's high and low, where many stop orders sit. "Swept" means price traded beyond it today. The **opening range** is the first 15 minutes' high and low.
- **VWAP and buyers %:** VWAP is today's volume-weighted average price. Buyers % is the share of volume that traded on up candles.
- **Index cards:** the same readings for the indices, with the next option expiry.
- **Careful:** the tiles' 5-minute bars are built from 1-minute closes, so their highs and lows are approximate. The chart window uses full candles, so zones can differ slightly between the two.

## 2. Sector Map
- **Bubble height** is the sector's move over the chosen horizon (today, week, month, 3 months). **Size** is the sector's total market value. The glowing line is the benchmark (Nifty 50 or the S&P 500): above it means beating the market.
- **RUNNING** means 1% or more ahead of the benchmark. The **light trail** shows where the sector was 30 minutes ago. Replay scrubs through the day.
- **US sectors** use ETFs (XLK, XLF and so on) as the sector line, with the S&P 1500 stocks inside. India uses NSE's own sector indices.
- **Inside a sector:** how many stocks are above their 50-day average, rose this week, sit within 5% of a 52-week high, or trade at 1.5 times normal volume. A sector rising on a few stocks is weaker than one rising on most.
- **Themes:** sub-industries with at least 5 stocks, showing the middle stock's move and how many beat the benchmark.

## 3. Swing Lab (the rules-based system)
The tested rule is a "VCP tightening break": buy a stock near its 52-week high after a quiet, tight base, when it closes above the 10-day high on heavy volume, but only while the market is healthy.
- **Market filter:** buying is allowed only while the benchmark closes above its 200-day average. OFF means no new buys. It uses daily closes, so it does not change with live prices.
- **R multiples:** profit in units of the risk taken. +3R made three times what the stop risked. -1R is a full stop-out. **Win rate** and **average R** together give expectancy.
- **Stop, target, time exit:** the stop sits under the 10-day low, the target is 3R, and the trade ends after 40 days at the latest.
- **CAGR, max drawdown, Sharpe:** yearly growth, the worst peak-to-trough fall, and return per unit of ups and downs. Compare with the equal-weight universe and the benchmark, which the lab shows beside the system.
- **Read it honestly:** the list is today's index members, so failed companies are missing, and every long backtest is flattered by that. In the US test this rule made less than buying the S&P 500.

## 4. Research note score
A 0 to 100 score from seven parts: business 15, growth 20, profitability 15, financial health 15, valuation 15, industry and economy 10, momentum 10. 75 and above is "Strong", 62 "Good", 48 "Average", 35 "Weak". It is built from reported results, so it describes the past, and a missing input is left out, not guessed.

## 5. Long Term
- **Screener scores** are percentiles among the list (100 is best): quality (return on equity, margins, cash generation, low debt, profitable years), growth (3-year sales, earnings and cash flow growth), value (earnings and cash flow against market value), trend (6 and 12 month move, above the 200-day average, near the high). Weights: quality 30, growth 25, value 25, trend 10, shareholder returns 10.
- **Ratios:** return on equity (profit over shareholders' money), margins (profit as a share of sales), free cash flow (operating cash minus capital spending, not shown for banks), debt over equity, share count (falling means buybacks, rising means dilution).
- **Valuation against its own history:** P/E and P/S each week for up to ten years. A low percentile means cheap against its own past, which can be a bargain or a business that got worse.
- **Insiders (US):** from Form 4 filings. Only open-market buys (P) and sales (S) show their own view. Grants, option exercises and tax withholding are pay. Sales say little on their own, since executives sell for taxes and diversification; buying with their own money is the rarer signal.
- **India holdings:** promoter and public share by quarter from NSE filings. A falling promoter share deserves a question.

## 6. All Stocks, alerts, watchlist
- **Breadth:** how many stocks rose and fell across every listing, and how many moved 5% or more.
- **Alerts:** a new structure break, a sweep of yesterday's high or low, a move past twice a normal day, and your watchlist triggers. Nothing fires while the market is closed.

## 7. Chart methods (the Methods button in the chart window)
Seven optional layers, all off until you switch them on. They are computed in the browser from the candles on screen with the standard settings, and checked against an independent calculation.
- **Ichimoku cloud (9, 26, 52):** the shaded cloud is support or resistance, and its colour says which of the two lines forming it is higher (green: leading span A above B). Price above the cloud is bullish, below is bearish, inside is indecision. The blue Tenkan line crossing above the red Kijun line is its buy-side signal, the reverse its sell-side signal. The grey dotted line is the price shifted back 26 bars (the lagging span). On daily charts the cloud is drawn 26 days ahead.
- **Bollinger Bands (20, 2):** a 20-bar average with bands two standard deviations away. Bands squeezing together mean volatility is low and a bigger move often follows; price hugging a band in a trend is strength, not a reversal by itself.
- **Supertrend (10, 3):** an ATR-based trailing line, green below price while the trend is up, red above while it is down. A flip of colour is a trend change signal and a ready-made stop level.
- **Donchian channel (20):** the highest high and lowest low of 20 bars; a close above the top is the classic breakout the Turtle traders used.
- **Keltner channel (20, 10, 2):** a 20-bar exponential average with bands two ATR away. A Bollinger band moving outside the Keltner channel is a common squeeze signal.
- **Anchored VWAP:** the average price paid by everyone since an anchor bar, weighted by volume. It starts at the lowest low of the last 120 bars; click any candle to move the anchor, for example to an earnings day or a swing low. Price above it means buyers since then are in profit.
- **Volume profile:** volume at each price over the bars you are looking at (it follows zoom and pan). The orange bar is the **point of control** (most traded price), the blue bars and the VAH and VAL lines mark the **value area** that holds 70% of the volume. Prices outside it are traded less and tend to be passed through faster.
Indices carry little or no volume, so the volume-based methods may show nothing there.

## 8. Screener methods (the Method menu in Long Term)
Each method filters and orders the same list. A missing figure is skipped, never filled.
- **Piotroski F-score:** nine yes/no tests of financial strength: profitable, positive operating cash flow, return on assets rising, cash earnings above reported earnings, debt falling, liquidity rising, no new shares, gross margin rising, asset turnover rising. 7 to 9 is strong. Banks are skipped, and the list shows tests passed out of tests that could be run.
- **Magic Formula (Greenblatt):** rank every company by earnings yield (operating profit over enterprise value) and by return on capital, add the two ranks; #1 is best. Here return on capital uses equity plus net debt as the capital base, an approximation, and banks are skipped.
- **Graham defensive tests:** P/E at most 15, P/B at most 1.5 (or P/E times P/B at most 22.5), current assets at least twice current liabilities, profit in every year on record, a dividend, and growing earnings.
- **PEG:** P/E divided by the yearly earnings growth over three years. Under 1 is read as cheap for its growth. A very small PEG usually comes from a tiny starting profit, so look at the growth number behind it.
- **Minervini trend template:** price above the 150 and 200-day averages, 150 above 200, the 200 rising for a month, 50 above 150 above 200, price above the 50, at least 25% above the 52-week low, within 25% of the 52-week high, and a relative strength rating of 70 or more.
- **Weinstein stage:** Stage 1 is a base, 2 an advance (price above a rising 30-week average), 3 a top, 4 a decline. Stage 2 is the one trend followers want.
- **Relative strength rating:** the 3, 6, 9 and 12-month returns weighted 40/20/20/20 and ranked 1 to 99 against the whole list.
- **Dual momentum (Antonacci):** a positive 12-month return (absolute) that also beats the market index (relative).

## 9. Market health and India's extra data
- **Market health panel (All Stocks):** the share of stocks above their 200-day and 50-day averages, 52-week highs against lows, rising against falling today, and the VIX. A market where the index rises on a shrinking number of stocks is narrower than it looks. The advance-decline line and the trend lines fill in with each market close. The thresholds shown (70% healthy, 40% weak, VIX 15 and 25) are conventions, not laws.
- **FII and DII flows (India):** foreign and domestic institutions' net buying in the cash market for the day, from NSE (provisional). Look at the run of days, not one.
- **Bulk, block and short deals (India):** large trades NSE publishes, with who bought or sold.
- **Option chain (India, chart window for indices and F&O stocks):** the **put/call ratio** (put open interest over call open interest), **max pain** (the expiry price at which option buyers lose the most), and the **walls**, the strikes with the most call open interest (resistance) and put open interest (support). The ladder chart shows open interest by strike around the current price, with now and max pain marked. Read these as tendencies: sellers defend their strikes, but walls do break.

## A sensible order to read it
1. **The market first:** index cards, the market filter, breadth.
2. **Sectors:** which are running and which are slipping, and whether most of their stocks agree.
3. **The tape:** the strongest and weakest stocks, and whether a CHoCH or a sweep is behind the move.
4. **The chart window:** the zones near price, then the research note and the long-term view to ask whether the business deserves the attention.
5. **Timing:** the swing system, the watchlist and the alerts.

## What it does not do
It does not forecast, size positions or manage risk for you. Prices come from Yahoo, a few seconds behind, and Sensex is 15 minutes late. Figures are as reported and may be restated. The history only contains survivors.

## Checking it for accuracy (for reviewers)
Pick five things and compare with a source you trust: a live price, a P/E, an earnings date, a sector's move, and a structure break on a 5-minute chart. Note any gap and the time you looked.
