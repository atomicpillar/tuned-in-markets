// Chart methods that different traders and analysts use, as optional layers on the chart window (all off by default):
// Ichimoku cloud, Bollinger Bands, Supertrend, Donchian channels, Keltner channels, anchored VWAP and a volume profile.
// Everything is computed here in the browser from the candles already on the chart, with the standard textbook settings.
(function () {
  const LIST = [
    ["ichimoku", "Ichimoku", "Ichimoku cloud (9, 26, 52): the cloud is support or resistance, price above it is bullish, below it bearish; Tenkan (blue) crossing Kijun (red) is its signal line"],
    ["boll", "Bollinger", "Bollinger Bands (20, 2): the average of 20 closes with bands 2 standard deviations away; narrow bands mean a squeeze"],
    ["super", "Supertrend", "Supertrend (10, 3): an ATR-based trailing line, green while the trend is up, red while it is down"],
    ["donch", "Donchian", "Donchian channel (20): the highest high and lowest low of the last 20 bars; a close above the top is a breakout"],
    ["kelt", "Keltner", "Keltner channel (20, 10, 2): a 20-bar average with bands 2 ATR away"],
    ["avwap", "Anchored VWAP", "Volume-weighted average price from an anchor bar: the average price paid by everyone since then. Click a candle to move the anchor"],
    ["vprof", "Volume profile", "Volume at each price over the bars on the chart: the longest bar is the point of control, the lines mark the 70% value area"]
  ];

  // ---------- maths ----------
  const roll = (a, n, f) => a.map((_, i) => i < n - 1 ? null : f(a.slice(i - n + 1, i + 1)));
  const sma = (a, n) => roll(a, n, w => w.reduce((s, x) => s + x, 0) / n);
  const hh = (a, n) => roll(a, n, w => Math.max(...w)), ll = (a, n) => roll(a, n, w => Math.min(...w));
  const ema = (a, n) => { const k = 2 / (n + 1); let p = null; return a.map((x, i) => { if (i < n - 1) return null; p = p == null ? a.slice(0, n).reduce((s, y) => s + y, 0) / n : x * k + p * (1 - k); return p; }); };
  const std = (a, n) => roll(a, n, w => { const m = w.reduce((s, x) => s + x, 0) / n; return Math.sqrt(w.reduce((s, x) => s + (x - m) ** 2, 0) / n); });
  const atr = (c, n) => {
    const tr = c.map((x, i) => i === 0 ? x.high - x.low : Math.max(x.high - x.low, Math.abs(x.high - c[i - 1].close), Math.abs(x.low - c[i - 1].close)));
    const out = c.map(() => null); let p = null;
    tr.forEach((t, i) => { if (i === n - 1) { p = tr.slice(0, n).reduce((s, x) => s + x, 0) / n; out[i] = p; } else if (i >= n) { p = (p * (n - 1) + t) / n; out[i] = p; } });
    return out;
  };
  const line = (c, v) => c.map((x, i) => v[i] == null ? null : {time: x.time, value: v[i]}).filter(Boolean);
  // future bar times: daily charts continue on weekdays; other timeframes do not project forward
  const future = (c, n, tf) => {
    if (tf !== "1d" || !c.length) return [];
    const out = []; let t = c.at(-1).time;
    while (out.length < n) { t += 86400; const d = new Date(t * 1000).getUTCDay(); if (d !== 0 && d !== 6) out.push(t); }
    return out;
  };

  function ichimoku(c, tf) {
    const h = c.map(x => x.high), l = c.map(x => x.low), cl = c.map(x => x.close);
    const mid = n => hh(h, n).map((x, i) => x == null ? null : (x + ll(l, n)[i]) / 2);
    const tenkan = mid(9), kijun = mid(26), b52 = mid(52);
    const a = tenkan.map((t, i) => t == null || kijun[i] == null ? null : (t + kijun[i]) / 2);
    const times = c.map(x => x.time).concat(future(c, 26, tf));
    const shift = v => v.map((x, i) => x == null ? null : {time: times[i + 26], value: x}).filter(p => p && p.time != null);
    const spanA = shift(a), spanB = shift(b52);
    const chikou = c.map((x, i) => i >= 26 ? {time: c[i - 26].time, value: cl[i]} : null).filter(Boolean);
    return {lines: [{d: line(c, tenkan), color: "#2563eb", w: 1.4, t: "Tenkan"}, {d: line(c, kijun), color: "#dc2626", w: 1.4, t: "Kijun"}, {d: chikou, color: "#9aa3b2", w: 1, style: 2, t: "Chikou"},
      {d: spanA, color: "rgba(34,160,90,.6)", w: 1, t: "Senkou A"}, {d: spanB, color: "rgba(220,63,84,.6)", w: 1, t: "Senkou B"}], fills: [{type: "cloud", a: spanA, b: spanB}]};
  }
  function bollinger(c) {
    const cl = c.map(x => x.close), m = sma(cl, 20), s = std(cl, 20), up = m.map((x, i) => x == null ? null : x + 2 * s[i]), lo = m.map((x, i) => x == null ? null : x - 2 * s[i]);
    return {lines: [{d: line(c, m), color: "#d97706", w: 1.2}, {d: line(c, up), color: "#7c3aed", w: 1}, {d: line(c, lo), color: "#7c3aed", w: 1}], fills: [{type: "band", up: line(c, up), lo: line(c, lo), color: "rgba(124,58,237,.07)"}]};
  }
  function supertrend(c) {
    const a = atr(c, 10), out = [];
    let fu = null, fl = null, trend = 1, st = null;
    c.forEach((x, i) => {
      if (a[i] == null) return;
      const mid = (x.high + x.low) / 2, bu = mid + 3 * a[i], bl = mid - 3 * a[i], pc = i > 0 ? c[i - 1].close : x.close;
      fu = fu == null || bu < fu || pc > fu ? bu : fu;
      fl = fl == null || bl > fl || pc < fl ? bl : fl;
      if (st == null) trend = x.close >= mid ? 1 : -1;
      else if (trend === 1 && x.close < fl) trend = -1;
      else if (trend === -1 && x.close > fu) trend = 1;
      st = trend === 1 ? fl : fu;
      out.push({time: x.time, value: st, color: trend === 1 ? "#22a05a" : "#dc3f54"});
    });
    return {lines: [{d: out, color: "#22a05a", w: 2}], fills: []};
  }
  function donchian(c) {
    const up = hh(c.map(x => x.high), 20), lo = ll(c.map(x => x.low), 20), mid = up.map((x, i) => x == null ? null : (x + lo[i]) / 2);
    return {lines: [{d: line(c, up), color: "#0891b2", w: 1.2}, {d: line(c, lo), color: "#0891b2", w: 1.2}, {d: line(c, mid), color: "#9aa3b2", w: 1, style: 2}], fills: [{type: "band", up: line(c, up), lo: line(c, lo), color: "rgba(8,145,178,.06)"}]};
  }
  function keltner(c) {
    const m = ema(c.map(x => x.close), 20), a = atr(c, 10), up = m.map((x, i) => x == null || a[i] == null ? null : x + 2 * a[i]), lo = m.map((x, i) => x == null || a[i] == null ? null : x - 2 * a[i]);
    return {lines: [{d: line(c, m), color: "#be185d", w: 1.2}, {d: line(c, up), color: "#be185d", w: 1, style: 2}, {d: line(c, lo), color: "#be185d", w: 1, style: 2}], fills: [{type: "band", up: line(c, up), lo: line(c, lo), color: "rgba(190,24,93,.05)"}]};
  }
  function avwap(c, anchor) {
    if (!c.length || !c.some(x => x.volume > 0)) return {lines: [], fills: [], note: "Anchored VWAP needs volume, which indices do not have."};
    let k = anchor != null ? c.findIndex(x => x.time >= anchor) : -1;
    if (k < 0) { const w = c.slice(-120); k = c.length - w.length + w.reduce((bi, x, i) => x.low < w[bi].low ? i : bi, 0); }       // default: the lowest low of the last 120 bars
    let pv = 0, v = 0; const out = [];
    for (let i = k; i < c.length; i++) { const x = c[i], tp = (x.high + x.low + x.close) / 3; pv += tp * (x.volume || 0); v += x.volume || 0; if (v > 0) out.push({time: x.time, value: pv / v}); }
    return {lines: [{d: out, color: "#0d9488", w: 2}], fills: [], anchorTime: c[k].time};
  }
  function vprofile(c) {
    if (!c.length || !c.some(x => x.volume > 0)) return {lines: [], fills: [], note: "Volume profile needs volume, which indices do not have."};
    return {lines: [], fills: [{type: "profile"}]};
  }
  // the profile of the bars currently in view: volume at each price, the point of control and the 70% value area
  function profileOf(c) {
    const lo = Math.min(...c.map(x => x.low)), hi = Math.max(...c.map(x => x.high)), N = 48, step = (hi - lo) / N || 1, bins = new Array(N).fill(0);
    c.forEach(x => { const a = Math.max(0, Math.floor((x.low - lo) / step)), b = Math.min(N - 1, Math.floor((x.high - lo) / step)), n = b - a + 1; for (let i = a; i <= b; i++) bins[i] += (x.volume || 0) / n; });
    const tot = bins.reduce((s, x) => s + x, 0), poc = bins.indexOf(Math.max(...bins));
    let a = poc, b = poc, acc = bins[poc];
    while (acc < tot * .7 && (a > 0 || b < N - 1)) { const up = b < N - 1 ? bins[b + 1] : -1, dn = a > 0 ? bins[a - 1] : -1; if (up >= dn) { b++; acc += bins[b]; } else { a--; acc += bins[a]; } }
    return {bins, lo, step, poc, a, b};
  }

  // ---------- applying to a chart ----------
  const FN = {ichimoku: ichimoku, boll: bollinger, super: supertrend, donch: donchian, kelt: keltner};
  function apply(MC, MS, candles, on, tf) {
    const st = MC.__meth || (MC.__meth = {series: [], fills: [], ctx: null, anchor: null, notes: []});
    st.ctx = {MC, MS, candles, on, tf};
    st.series.forEach(s => { try { MC.removeSeries(s); } catch (e) {} }); st.series = []; st.fills = []; st.notes = [];
    if (!MC.__click) { MC.__click = true; MC.subscribeClick(p => { const s = MC.__meth; if (p && p.time && s && s.ctx && s.ctx.on.avwap) { s.anchor = p.time; apply(s.ctx.MC, s.ctx.MS, s.ctx.candles, s.ctx.on, s.ctx.tf); } }); }
    if (!candles || candles.length < 30) return;
    for (const [id] of LIST) {
      if (!on[id]) continue;
      const r = id === "avwap" ? avwap(candles, st.anchor) : id === "vprof" ? vprofile(candles) : FN[id](candles, tf);
      if (r.note) st.notes.push(r.note);
      (r.lines || []).forEach(l => {
        if (!l.d.length) return;
        const s = MC.addLineSeries({color: l.color, lineWidth: l.w || 1, lineStyle: l.style || 0, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: ""});
        s.setData(l.d); st.series.push(s);
      });
      st.fills.push(...(r.fills || []));
    }
  }
  function draw(x, MC, MS, pw, ph) {
    const st = MC.__meth; if (!st || !st.fills.length) return;
    const X = t => MC.timeScale().timeToCoordinate(t), Y = v => MS.priceToCoordinate(v);
    for (let f of st.fills) {
      if (f.type === "cloud") {
        const bm = new Map(f.b.map(p => [p.time, p.value]));
        const pts = f.a.filter(p => bm.has(p.time)).map(p => ({x: X(p.time), a: Y(p.value), b: Y(bm.get(p.time)), up: p.value >= bm.get(p.time)})).filter(p => p.x != null && p.a != null && p.b != null);
        for (let i = 1; i < pts.length; i++) { const p = pts[i - 1], q = pts[i]; x.fillStyle = q.up ? "rgba(34,160,90,.16)" : "rgba(220,63,84,.16)"; x.beginPath(); x.moveTo(p.x, p.a); x.lineTo(q.x, q.a); x.lineTo(q.x, q.b); x.lineTo(p.x, p.b); x.closePath(); x.fill(); }
      } else if (f.type === "band") {
        const lm = new Map(f.lo.map(p => [p.time, p.value]));
        const pts = f.up.filter(p => lm.has(p.time)).map(p => ({x: X(p.time), a: Y(p.value), b: Y(lm.get(p.time))})).filter(p => p.x != null && p.a != null && p.b != null);
        for (let i = 1; i < pts.length; i++) { const p = pts[i - 1], q = pts[i]; x.fillStyle = f.color; x.beginPath(); x.moveTo(p.x, p.a); x.lineTo(q.x, q.a); x.lineTo(q.x, q.b); x.lineTo(p.x, p.b); x.closePath(); x.fill(); }
      } else if (f.type === "profile") {
        const rg = MC.timeScale().getVisibleLogicalRange(), cs = st.ctx.candles;
        const view = rg ? cs.slice(Math.max(0, Math.floor(rg.from)), Math.min(cs.length, Math.ceil(rg.to) + 1)) : cs;
        if (view.length < 5) continue;
        f = profileOf(view);
        const mx = Math.max(...f.bins), maxW = Math.min(150, pw * .22);
        f.bins.forEach((v, i) => {
          const y1 = Y(f.lo + (i + 1) * f.step), y2 = Y(f.lo + i * f.step); if (y1 == null || y2 == null) return;
          const inVA = i >= f.a && i <= f.b; x.fillStyle = i === f.poc ? "rgba(217,119,6,.55)" : inVA ? "rgba(37,99,235,.28)" : "rgba(154,163,178,.28)";
          x.fillRect(pw - v / mx * maxW, y1 + .5, v / mx * maxW, Math.max(1, y2 - y1 - 1));
        });
        const lab = (i, t, c) => { const y = Y(i); if (y == null) return; x.strokeStyle = c; x.setLineDash([3, 3]); x.beginPath(); x.moveTo(pw - maxW - 4, y); x.lineTo(pw, y); x.stroke(); x.setLineDash([]); x.fillStyle = c; x.font = "600 10px JetBrains Mono"; x.fillText(t, pw - maxW - 38, y + 3); };
        lab(f.lo + (f.poc + .5) * f.step, "POC", "#b45309"); lab(f.lo + (f.b + 1) * f.step, "VAH", "#1d4ed8"); lab(f.lo + f.a * f.step, "VAL", "#1d4ed8");
      }
    }
    if (st.notes.length) { x.fillStyle = "#6b7487"; x.font = "11px Inter"; x.fillText(st.notes[0], 8, ph - 34); }
  }
  window.Methods = {LIST, apply, draw, _math: {sma, ema, std, atr, hh, ll, ichimoku, bollinger, supertrend, donchian, keltner, avwap, vprofile, profileOf}};
})();
