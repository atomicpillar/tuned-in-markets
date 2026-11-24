// Market profiles. India's values are exactly what the pages always used; the US profile swaps hours, currency,
// benchmark, index cards and wording. The pages read window.MK; the switcher in index.html picks the profile.
(function () {
  const IN = {
    id: "IN", label: "India", tzName: "IST", rsTitle: "Strength vs Nifty (3 months)", cur: "₹", loc: "en-IN", tz: "Asia/Kolkata", open: 555, sess: 375, eod: "15:15",
    bench: "NIFTY 50", benchS: "NIFTY", benchTitle: "Nifty", exch: "NSE",
    idx: [["NIFTY", "NIFTY"], ["BANKNIFTY", "BANKNIFTY"], ["SENSEX", "SENSEX"]],
    idxSet: ["NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY"],
    ticks: [["09:15", 0], ["10:00", 45], ["11:00", 105], ["12:00", 165], ["13:00", 225], ["14:00", 285], ["15:00", 345]],
    mcap: v => "₹" + Math.round(v / 1e7).toLocaleString("en-IN") + " cr",
    unit: "cr", unitName: "₹ crore", src: "NSE filings", filer: "NSE", tape: "F&O",
    t: {}
  };
  const US = {
    id: "US", label: "US", tzName: "ET", rsTitle: "Strength vs S&P 500 (3 months)", cur: "$", loc: "en-US", tz: "America/New_York", open: 570, sess: 390, eod: "15:45",
    bench: "S&P 500", benchS: "S&P 500", benchTitle: "S&P 500", exch: "the US exchanges",
    idx: [["SPX", "S&P 500"], ["NDX", "NASDAQ-100"], ["DJI", "DOW"]],
    idxSet: ["SPX", "NDX", "DJI"],
    ticks: [["09:30", 0], ["10:30", 60], ["11:30", 120], ["12:30", 180], ["13:30", 240], ["14:30", 300], ["15:30", 360]],
    mcap: v => v >= 1e12 ? "$" + (v / 1e12).toFixed(2) + "T" : "$" + (v / 1e9).toFixed(v >= 1e10 ? 0 : 1) + "B",
    unit: "M", unitName: "$ million", src: "SEC filings", filer: "the SEC", tape: "S&P 500 + Nasdaq-100",
    t: {
      smSub: "Every S&amp;P 500 and Nasdaq-100 stock and the S&amp;P 500, NASDAQ-100 and DOW: displacement, structure, zones and liquidity, live",
      smNote: "Lines: every S&amp;P 500 and Nasdaq-100 stock's move since the open (green above, red below), indices dashed. Waterfall: every stock now, strongest at the top; the 20 strongest and 20 weakest connect to their tiles. Hover a line, a bar, a bead or a tile to follow one stock; hover a sector to see its stocks. Click to open its chart. Displacement = move since the open ÷ a normal day's range. Prices from Yahoo, a few seconds behind (indices every 4 s, stocks every 12 s). A technical screen, not advice.",
      labSub: "Holds of 2–40 days in a cash account, tested on 5 years of S&amp;P 1500 stocks after every cost. Click any stock on this page: its chart opens on the daily view with every past trade, the setup right now and its risk:reward.",
      costWord: "trading", benchName: "S&amp;P 500", cashName: "In cash: S&amp;P 500 under its 200-DMA",
      secSub: "Which sectors are running, what is moving them, and the stocks inside (S&amp;P 1500)",
      secFoot: "A technical screen built from Yahoo and SEC data · prices a few seconds behind for what is on screen, about a minute for the rest · ETF sector moves, not official index values · not investment advice"
    }
  };
  const all = {IN, US};
  const pick = () => { try { return localStorage.getItem("mlab.market") || "IN"; } catch (e) { return "IN"; } };
  const url = new URLSearchParams(location.search).get("m");
  const id = (url && all[url.toUpperCase()]) ? url.toUpperCase() : pick();

  // minutes ahead of UTC that the exchange's clock is at a given instant (handles daylight saving)
  const offMin = (tz, ms) => {
    const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", {timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit"}).formatToParts(new Date(ms)).map(x => [x.type, x.value]));
    return (Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute) - Math.floor(ms / 60000) * 60000) / 60000;
  };
  for (const m of Object.values(all)) {
    m.names = Object.fromEntries(m.idx);
    m.keys = m.idx.map(x => x[0]);
    // minutes into the trading day, kept between 1 and the session length
    m.nowMin = () => Math.max(1, Math.min(m.sess, Math.floor((Date.now() / 60000 + offMin(m.tz, Date.now())) % 1440) - m.open));
    // the UTC second at which a given exchange date's session opens (a daily candle's time)
    m.dayOpen = day => { const guess = Date.parse(day + "T00:00:00Z") + m.open * 60000; return (guess - offMin(m.tz, guess) * 60000) / 1000; };
    m.num = (v, d = 2) => Number(v).toLocaleString(m.loc, {minimumFractionDigits: d, maximumFractionDigits: d});
  }
  window.MARKETS = all;
  window.MK = all[id];
  window.setMarket = k => { try { localStorage.setItem("mlab.market", k); } catch (e) {} const u = new URL(location.href); u.searchParams.set("m", k); location.href = u.toString(); };
  // every API call carries the market, so the same pages talk to the right engine
  const f = window.fetch.bind(window);
  window.fetch = (u, o) => (typeof u === "string" && u.startsWith("/api/") && window.MK.id === "US") ? f(u + (u.includes("?") ? "&" : "?") + "mkt=US", o) : f(u, o);
  // chart time axis: lightweight-charts labels in UTC by default, so ticks are formatted in the market's own time zone (the crosshair already is)
  window.tickFmt = (t, type) => {
    const d = new Date(t * 1000), o = {timeZone: window.MK.tz};
    if (type === 0) return d.toLocaleString(window.MK.loc, {...o, year: "numeric"});
    if (type === 1) return d.toLocaleString(window.MK.loc, {...o, month: "short"});
    if (type === 2) return d.toLocaleString(window.MK.loc, {...o, day: "numeric"});
    return d.toLocaleTimeString("en-GB", {...o, hour: "2-digit", minute: "2-digit", ...(type === 4 ? {second: "2-digit"} : {})});
  };
})();
