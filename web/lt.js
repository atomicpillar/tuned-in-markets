// Long-term view of one stock, drawn inside the chart window (under the research note): ten years of fundamentals, ratios,
// valuation against its own history, earnings, dividends, ownership and insiders, with the watchlist button.
// Every block names its source; a figure that is missing shows a dash and is never filled in.
(function () {
  const esc = x => String(x ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const MKr = () => window.MK;
  const num = (v, d = 1) => v == null || !isFinite(v) ? "–" : Number(v).toLocaleString(MKr().loc, {minimumFractionDigits: d, maximumFractionDigits: d});
  const pct = (v, d = 1) => v == null || !isFinite(v) ? "–" : (v > 0 ? "+" : "") + num(v, d) + "%";
  const pc0 = (v, d = 1) => v == null || !isFinite(v) ? "–" : num(v, d) + "%";
  const money = v => {
    if (v == null || !isFinite(v)) return "–";
    if (MKr().id === "US") { const a = Math.abs(v), s = v < 0 ? "-" : ""; return s + "$" + (a >= 1000 ? num(a / 1000, 1) + "B" : num(a, 0) + "M"); }
    return "₹" + Math.round(v).toLocaleString("en-IN") + " cr";
  };
  const CSS = `.lt{margin-top:12px;font:12.5px/1.45 Inter,system-ui,sans-serif;color:#121826}
.lt .lt-card{background:#fff;border:1px solid #e1e5ec;border-radius:12px;padding:12px 14px;margin-top:10px}
.lt .lt-h{font:600 10.5px "JetBrains Mono",monospace;letter-spacing:.6px;color:#6b7487;margin-bottom:8px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.lt .lt-h b{color:#121826}.lt .src{font-weight:500;letter-spacing:0;color:#8a93a6;text-transform:none}
.lt .lt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}
.lt .lt-kv{background:#f6f8fb;border-radius:8px;padding:7px 9px}.lt .lt-kv span{display:block;font-size:10.5px;color:#6b7487}.lt .lt-kv b{font:600 14px "JetBrains Mono",monospace}
.lt .lt-two{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:900px){.lt .lt-two{grid-template-columns:1fr}}
.lt .lt-ch{background:#f6f8fb;border-radius:8px;padding:8px 10px}.lt .lt-ch h5{margin:0 0 4px;font-size:11px;font-weight:600;color:#44506a;display:flex;justify-content:space-between}
.lt svg{width:100%;height:auto;display:block}.lt svg text{font:9px Inter,sans-serif;fill:#6b7487}
.lt table{width:100%;border-collapse:collapse;font-size:12px}.lt th{text-align:left;font-weight:600;color:#6b7487;font-size:10.5px;padding:3px 6px 3px 0}.lt td{padding:3px 6px 3px 0;border-top:1px solid #eef1f5}
.lt td.r,.lt th.r{text-align:right;font-family:"JetBrains Mono",monospace}
.lt .up{color:#22a05a}.lt .down{color:#dc3f54}.lt .muted{color:#6b7487}
.lt .btn{border:1px solid #d9dee6;background:#fff;border-radius:8px;padding:5px 11px;font:600 12px Inter,sans-serif;cursor:pointer;color:#121826}
.lt .btn.pri{background:#141a26;border-color:#141a26;color:#fff}.lt .btn:disabled{opacity:.5}
.lt input,.lt textarea{border:1px solid #d9dee6;border-radius:8px;padding:6px 8px;font:12.5px Inter,sans-serif;width:100%;box-sizing:border-box}
.lt .note{font-size:11px;color:#6b7487;line-height:1.5}
.lt .lt-load{color:#6b7487;padding:10px 2px}`;

  // ---------- small SVG charts ----------
  function bars(vals, labels, opts = {}) {
    const W = 300, H = opts.h || 96, n = vals.length, ok = vals.filter(v => v != null && isFinite(v));
    if (!ok.length) return '<div class="muted" style="padding:14px 0">No filed figures.</div>';
    const hi = Math.max(0, ...ok), lo = Math.min(0, ...ok), span = (hi - lo) || 1, bw = W / n, Y = v => 6 + (hi - v) / span * (H - 24), z = Y(0);
    const rects = vals.map((v, i) => v == null ? "" : `<rect x="${i * bw + bw * .15}" y="${Math.min(Y(v), z)}" width="${bw * .7}" height="${Math.max(1, Math.abs(Y(v) - z))}" rx="1.5" fill="${v >= 0 ? (opts.color || "#8fb3ee") : "#e88a9a"}"><title>${esc(labels[i])}: ${opts.fmt ? opts.fmt(v) : num(v, 1)}</title></rect>`).join("");
    const lab = labels.map((l, i) => (n <= 6 || i % 2 === (n - 1) % 2) ? `<text x="${i * bw + bw / 2}" y="${H - 3}" text-anchor="middle">${esc(l)}</text>` : "").join("");
    return `<svg viewBox="0 0 ${W} ${H}"><line x1="0" x2="${W}" y1="${z}" y2="${z}" stroke="#d5dae3"/>${rects}${lab}</svg>`;
  }
  function lines(series, labels, opts = {}) {
    const W = 300, H = opts.h || 110, all = series.flatMap(s => s.v).filter(v => v != null && isFinite(v));
    if (all.length < 2) return '<div class="muted" style="padding:14px 0">Not enough history.</div>';
    all.sort((a, b) => a - b);
    const hi = opts.max != null ? opts.max : all[Math.floor(all.length * .985)], lo = Math.min(opts.min != null ? opts.min : all[0], 0 === opts.zero ? 0 : all[0]), span = (hi - lo) || 1;
    const n = labels.length, X = i => 4 + i / (n - 1) * (W - 8), Y = v => 6 + (hi - Math.min(hi, Math.max(lo, v))) / span * (H - 22);
    let g = "";
    if (opts.band) g += `<rect x="4" y="${Y(opts.band[1])}" width="${W - 8}" height="${Math.max(1, Y(opts.band[0]) - Y(opts.band[1]))}" fill="#e6edf8"/>`;
    if (opts.median != null) g += `<line x1="4" x2="${W - 4}" y1="${Y(opts.median)}" y2="${Y(opts.median)}" stroke="#9aa3b2" stroke-dasharray="3 3"/><text x="${W - 4}" y="${Y(opts.median) - 3}" text-anchor="end">median ${num(opts.median, 1)}</text>`;
    for (const s of series) {
      let d = "", pen = false;
      s.v.forEach((v, i) => { if (v == null || !isFinite(v)) { pen = false; return; } d += `${pen ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; pen = true; });
      g += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.w || 1.6}" ${s.dash ? 'stroke-dasharray="4 3"' : ""}/>`;
      const li = s.v.map((v, i) => v != null && isFinite(v) ? i : -1).filter(i => i >= 0).pop();
      if (li != null && li >= 0 && !s.nodot) g += `<circle cx="${X(li)}" cy="${Y(s.v[li])}" r="2.6" fill="${s.color}"/>`;
    }
    const ticks = [0, Math.floor(n / 3), Math.floor(2 * n / 3), n - 1].map(i => `<text x="${X(i)}" y="${H - 3}" text-anchor="${i === 0 ? "start" : i === n - 1 ? "end" : "middle"}">${esc(String(labels[i]).slice(0, 7))}</text>`).join("");
    return `<svg viewBox="0 0 ${W} ${H}">${g}${ticks}</svg>`;
  }
  const kv = (l, v, cls = "") => v == null || v === "–" ? "" : `<div class="lt-kv"><span>${esc(l)}</span><b class="${cls}">${v}</b></div>`;

  async function watchState(sym) {
    try { const d = await (await fetch("/api/lt/watch")).json(); return (d.rows || []).find(r => r.sym === sym) || null; } catch (e) { return null; }
  }
  async function post(body) {
    return (await fetch("/api/lt/watch", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json();
  }

  function render(el, sym, d) {
    const r = d.ratios || {}, A = d.annual || [], Q = d.quarterly || [], u = d.unit || "";
    const fy = A.map(a => String(a.fy).slice(2)), lab = A.map(a => a.end.slice(0, 7));
    const col = k => A.map(a => a[k]);
    const kvs = [kv("Return on equity", pc0(r.roe)), kv("Operating margin", pc0(r.op_margin)), kv("Net margin", pc0(r.net_margin)), kv("Free cash flow margin", pc0(r.fcf_margin)),
      kv("Debt ÷ equity", r.debt_equity == null ? null : num(r.debt_equity, 2) + "×"), kv("Net cash (cash − debt)", r.net_cash == null ? null : money(r.net_cash), r.net_cash >= 0 ? "up" : "down"),
      kv("Revenue growth / yr, 3 y", pct(r.rev_cagr3), r.rev_cagr3 >= 0 ? "up" : "down"), kv("Revenue growth / yr, 5 y", pct(r.rev_cagr5), r.rev_cagr5 >= 0 ? "up" : "down"),
      kv("Earnings per share, 3 y", pct(r.eps_cagr3), r.eps_cagr3 >= 0 ? "up" : "down"), kv("Earnings per share, 5 y", pct(r.eps_cagr5), r.eps_cagr5 >= 0 ? "up" : "down"),
      kv("Free cash flow, 3 y", pct(r.fcf_cagr3), r.fcf_cagr3 >= 0 ? "up" : "down"), kv("Share count, 3 y", pct(r.share_change3), r.share_change3 <= 0 ? "up" : "down"),
      kv("Profitable years", r.n_years_net ? `${r.profitable_years} of ${r.n_years_net}` : null), kv("Dividend payout", r.payout == null ? null : pc0(r.payout, 0))].join("");
    const pe = d.pe_stats, ps = d.ps_stats, V = d.valuation;
    const vtxt = (s, name) => s ? `${name} <b>${num(s.now, 1)}</b> now · median <b>${num(s.median, 1)}</b> · range ${num(s.low, 1)} to ${num(s.high, 1)} · <b>${s.pctile}th</b> percentile of its own ${s.n} weeks` : "";
    const val = V ? `<div class="lt-card"><div class="lt-h"><b>VALUATION AGAINST ITS OWN HISTORY</b><span class="src">price ÷ earnings and price ÷ sales, ${MKr().id === "US" ? "each week using only filings public by then" : "from each year's reported EPS"}</span></div>
      <div class="lt-two"><div class="lt-ch"><h5><span>Price ÷ earnings</span></h5>${pe ? lines([{v: V.pe, color: "#2563eb"}], V.dates, {band: [pe.p25, pe.p75], median: pe.median, min: 0}) : '<div class="muted">Earnings not positive or too short.</div>'}<div class="note">${vtxt(pe, "P/E")}</div></div>
      <div class="lt-ch"><h5><span>Price ÷ sales</span></h5>${ps ? lines([{v: V.ps, color: "#7c3aed"}], V.dates, {band: [ps.p25, ps.p75], median: ps.median, min: 0}) : '<div class="muted">Not enough history.</div>'}<div class="note">${vtxt(ps, "P/S")}</div></div></div>
      <div class="note" style="margin-top:6px">A low percentile means cheap against its own past, which can be a bargain or a business that got worse. The shaded band is the middle half of its history.</div></div>` : "";
    const P = d.price;
    const price = P ? `<div class="lt-ch"><h5><span>Price, weekly, ${P.dates.length} weeks</span><span class="muted">52-week ${num(P.low52, 2)} to ${num(P.high52, 2)}</span></h5>${lines([{v: P.close, color: "#121826", nodot: true}, {v: P.sma200, color: "#d97706", dash: true, nodot: true, w: 1.2}], P.dates, {h: 110})}<div class="note">Black: weekly close. Dashed: 40-week average (about 200 days).</div></div>` : "";
    const sh = col("shares");
    const dyears = {}; (d.dividends || []).forEach(x => { const y = x.date.slice(0, 4); dyears[y] = (dyears[y] || 0) + x.amount; });
    const dy = Object.keys(dyears).slice(-10);
    const charts = A.length ? `<div class="lt-card"><div class="lt-h"><b>FUNDAMENTALS, ${A.length} FISCAL YEARS</b><span class="src">${esc(d.source)}</span></div>
      <div class="lt-grid">${kvs}</div>
      <div class="lt-two" style="margin-top:10px">
        <div class="lt-ch"><h5><span>Revenue</span><span class="muted">${esc(u)}</span></h5>${bars(col("revenue"), fy, {fmt: money})}</div>
        <div class="lt-ch"><h5><span>Net profit</span><span class="muted">${esc(u)}</span></h5>${bars(col("net"), fy, {fmt: money, color: "#8fd0a8"})}</div>
        ${d.financial ? "" : `<div class="lt-ch"><h5><span>Free cash flow</span><span class="muted">operating cash − capex</span></h5>${bars(col("fcf"), fy, {fmt: money, color: "#e7c37a"})}</div>`}
        <div class="lt-ch"><h5><span>Margins</span><span class="muted"><span style="color:#2563eb">gross</span> · <span style="color:#d97706">operating</span> · <span style="color:#16a34a">net</span></span></h5>${lines([
          {v: A.map(a => a.gross != null && a.revenue ? a.gross / a.revenue * 100 : null), color: "#2563eb"}, {v: A.map(a => a.opinc != null && a.revenue ? a.opinc / a.revenue * 100 : null), color: "#d97706"},
          {v: A.map(a => a.net != null && a.revenue ? a.net / a.revenue * 100 : null), color: "#16a34a"}], lab, {zero: 0})}</div>
        <div class="lt-ch"><h5><span>Shares outstanding (diluted average)</span><span class="muted">millions</span></h5>${sh.filter(v => v != null).length > 1 ? lines([{v: sh, color: "#7c3aed"}], lab, {min: Math.min(...sh.filter(v => v != null)) * .9}) : '<div class="muted">Not filed.</div>'}</div>
        ${d.financial ? "" : `<div class="lt-ch"><h5><span>Debt and cash</span><span class="muted"><span style="color:#dc3f54">debt</span> · <span style="color:#22a05a">cash</span></span></h5>${lines([{v: col("debt"), color: "#dc3f54"}, {v: col("cash"), color: "#22a05a"}], lab, {zero: 0})}</div>`}
        ${price}
        ${dy.length ? `<div class="lt-ch"><h5><span>Dividend per share, by year</span></h5>${bars(dy.map(y => dyears[y]), dy.map(y => y.slice(2)), {fmt: v => num(v, 2), color: "#9bd0e8"})}</div>` : ""}
      </div></div>` : `<div class="lt-card"><div class="lt-h"><b>FUNDAMENTALS</b><span class="src">${esc(d.source || "")}</span></div><div class="muted">No filed statements found for this ticker. ${price ? "" : ""}</div>${price ? `<div class="lt-two" style="margin-top:8px">${price}</div>` : ""}</div>`;
    const ev = d.events || {}, eh = (ev.earnings || []);
    const dv = ev.dividend;
    const earn = `<div class="lt-card"><div class="lt-h"><b>EARNINGS AND DIVIDENDS</b><span class="src">${esc(ev.source || "Yahoo Finance")}</span></div>
      <div class="lt-grid">${kv("Next earnings", ev.next_earnings || "not announced")}${dv ? kv("Dividend yield", pc0(dv.yield, 2)) + kv("Dividend per share, yearly", num(dv.rate, 2)) + kv("Last ex-dividend date", dv.ex_date) + kv("Payout", dv.payout == null ? null : pc0(dv.payout, 0)) : kv("Dividend", "none paid")}</div>
      ${eh.length ? `<table style="margin-top:8px"><tr><th>Quarter</th><th class="r">Reported EPS</th><th class="r">Analysts expected</th><th class="r">Surprise</th></tr>${eh.map(e => `<tr><td>${esc(e.quarter || "")}</td><td class="r">${num(e.actual, 2)}</td><td class="r">${num(e.estimate, 2)}</td><td class="r ${e.surprise_pct >= 0 ? "up" : "down"}">${pct(e.surprise_pct)}</td></tr>`).join("")}</table>` : ""}</div>`;
    const ow = d.ownership || {}, h = ow.holders, it = ow.insider_trades, sr = ow.shareholding;
    let own = "";
    if (h || it || sr) {
      own = `<div class="lt-card"><div class="lt-h"><b>OWNERSHIP AND INSIDERS</b><span class="src">${[h && h.source, it && it.source, sr && sr.source].filter(Boolean).map(esc).join(" · ")}</span></div>`;
      if (h) own += `<div class="lt-grid">${kv("Held by insiders", pc0(h.insiders_pct))}${kv("Held by institutions", pc0(h.institutions_pct))}${kv("Institutions holding", h.institutions_count == null ? null : Number(h.institutions_count).toLocaleString(MKr().loc))}</div>`;
      if (sr && sr.rows.length) own += `<div class="lt-ch" style="margin-top:8px"><h5><span>${MKr().id === "IN" ? "Promoter" : "Insider"} and public holding by quarter</span><span class="muted"><span style="color:#2563eb">promoter</span> · <span style="color:#9aa3b2">public</span></span></h5>${lines([{v: sr.rows.map(x => x.promoter), color: "#2563eb"}, {v: sr.rows.map(x => x.public), color: "#9aa3b2"}], sr.rows.map(x => x.date), {min: Math.max(0, Math.floor(Math.min(...sr.rows.map(x => Math.min(x.promoter, x.public))) - 4)), max: Math.min(100, Math.ceil(Math.max(...sr.rows.map(x => Math.max(x.promoter, x.public))) + 4))})}<div class="note">Latest: promoter ${num(sr.rows.at(-1).promoter, 2)}% · public ${num(sr.rows.at(-1).public, 2)}% (${esc(sr.rows.at(-1).date)})</div></div>`;
      if (it) own += `<div style="margin-top:10px"><div class="lt-h"><b>INSIDER TRADES, LAST ${it.days} DAYS</b><span class="src">${it.filings} Form 4 filings read; only open-market buys and sales count as their own view</span></div>
        <div class="lt-grid">${kv("Open-market buys", it.buys.n ? `${it.buys.n} by ${it.buys.people} · $${num(it.buys.value_m, 1)}M` : "none", it.buys.n ? "up" : "")}${kv("Open-market sales", it.sells.n ? `${it.sells.n} by ${it.sells.people} · $${num(it.sells.value_m, 1)}M` : "none", it.sells.n ? "down" : "")}${kv("Grants, exercises, tax withholding", it.other)}</div>
        ${it.recent.length ? `<table style="margin-top:8px"><tr><th>Date</th><th>Who</th><th>What</th><th class="r">Shares</th><th class="r">Price</th></tr>${it.recent.map(t => `<tr><td>${esc(t.date)}</td><td>${esc(t.owner)}<div class="muted" style="font-size:10.5px">${esc(t.title)}</div></td><td class="${t.code === "P" ? "up" : "down"}">${esc(t.what)}</td><td class="r">${Math.round(t.shares).toLocaleString(MKr().loc)}</td><td class="r">${num(t.price, 2)}</td></tr>`).join("")}</table>` : ""}
        <div class="note" style="margin-top:4px">Executives sell mostly to pay taxes and diversify, so selling says little on its own; buying with their own money is the rarer, stronger signal.</div></div>`;
      if (h && h.top && h.top.length) own += `<table style="margin-top:10px"><tr><th>Largest institutional holders</th><th class="r">% held</th><th class="r">Shares</th><th class="r">As of</th></tr>${h.top.map(t => `<tr><td>${esc(t.name)}</td><td class="r">${num(t.pct, 2)}%</td><td class="r">${t.shares == null ? "–" : Number(t.shares).toLocaleString(MKr().loc)}</td><td class="r">${esc(t.date || "")}</td></tr>`).join("")}</table>`;
      own += "</div>";
    }
    const notes = (d.notes || []).concat(ow.insider_trades_error || [], ow.shareholding_error || []);
    return `${charts}${val}${earn}${own}<div class="note" style="margin-top:10px">Figures are as reported by the companies and may be restated later. The screener and history use today's index members, so companies that failed are missing: a long history shows how a business behaved, it does not prove it will keep doing so.${notes.length ? " " + notes.map(esc).join(" ") : ""}</div>`;
  }

  function head(sym, d, w) {
    const on = !!w;
    return `<div class="lt-card" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><div class="lt-h" style="margin:0;flex:1"><b>LONG-TERM VIEW</b><span class="src">built ${new Date(d.built * 1000).toLocaleString(MKr().loc)}</span></div>
      <button class="btn ${on ? "" : "pri"}" id="ltw">${on ? "On your watchlist · edit" : "Add to watchlist"}</button></div><div id="ltwf"></div>`;
  }
  function wform(el, sym, d, w) {
    const box = el.querySelector("#ltwf"), last = d.price && d.price.last;
    box.innerHTML = `<div class="lt-card"><div style="display:grid;grid-template-columns:1fr 160px;gap:8px"><div><div class="muted" style="font-size:11px">Why is it on your list?</div><textarea id="ltn" rows="2" placeholder="Your own note">${esc(w ? w.note : "")}</textarea></div>
      <div><div class="muted" style="font-size:11px">Tell me at this price (optional)</div><input id="ltt" type="number" step="any" placeholder="${last ? "now " + last : ""}" value="${w && w.target != null ? w.target : ""}"></div></div>
      <div style="margin-top:8px;display:flex;gap:8px"><button class="btn pri" id="lts">${w ? "Save" : "Add"}</button>${w ? '<button class="btn" id="ltr">Remove</button>' : ""}<button class="btn" id="ltc">Close</button></div></div>`;
    box.querySelector("#ltc").onclick = () => { box.innerHTML = ""; };
    box.querySelector("#lts").onclick = async () => {
      const t = box.querySelector("#ltt").value, body = {sym, note: box.querySelector("#ltn").value, target: t === "" ? null : +t};
      await post(w ? {action: "update", ...body} : {action: "add", price: last, ...body});
      window.longBox(el, sym, true);
    };
    const rm = box.querySelector("#ltr"); if (rm) rm.onclick = async () => { await post({action: "remove", sym}); window.longBox(el, sym, true); };
  }

  window.longBox = async (el, sym, keep) => {
    if (!el) return;
    if (!sym || window.MK.idxSet.includes(sym) || String(sym).startsWith("^")) { el.innerHTML = ""; return; }
    if (!keep) el.dataset.sym = sym;
    const root = el.getRootNode();
    if (root && root.querySelector && !root.querySelector("#ltcss")) { const s = document.createElement("style"); s.id = "ltcss"; s.textContent = CSS; (root.host ? root : document.head).appendChild(s); }
    if (!keep) el.innerHTML = `<div class="lt"><div class="lt-card lt-load">Reading ${esc(sym)}'s filings, prices and holders… (the first time takes up to 20 seconds)</div></div>`;
    let d; try { d = await (await fetch(`/api/lt/stock?sym=${encodeURIComponent(sym)}`)).json(); } catch (e) { d = {error: "unavailable"}; }
    if (el.dataset.sym !== sym) return;
    if (d.error) { el.innerHTML = `<div class="lt"><div class="lt-card muted">Long-term view unavailable right now.</div></div>`; return; }
    const w = await watchState(sym);
    el.innerHTML = `<div class="lt">${head(sym, d, w)}${render(el, sym, d)}</div>`;
    el.querySelector("#ltw").onclick = () => wform(el, sym, d, w);
  };

  // ---------- options (India): put/call ratio, max pain and the open-interest walls for the nearest expiry ----------
  window.optBox = async (el, sym) => {
    if (!el) return;
    if (window.MK.id !== "IN" || !sym || String(sym).startsWith("^")) { el.innerHTML = ""; return; }
    el.dataset.osym = sym;
    let d; try { d = await (await fetch(`/api/in/options?sym=${encodeURIComponent(sym)}`)).json(); } catch (e) { return; }
    if (el.dataset.osym !== sym) return;
    if (d.error) { el.innerHTML = ""; return; }
    const root = el.getRootNode();
    if (root && root.querySelector && !root.querySelector("#ltcss")) { const s = document.createElement("style"); s.id = "ltcss"; s.textContent = CSS; (root.host ? root : document.head).appendChild(s); }
    const L = d.ladder, mx = Math.max(...L.map(x => Math.max(x.call_oi, x.put_oi))) || 1, W = 300, H = 120, bw = W / L.length;
    const bars = L.map((x, i) => { const hc = x.call_oi / mx * (H - 26), hp = x.put_oi / mx * (H - 26), x0 = i * bw;
      return `<rect x="${x0 + bw * .08}" y="${H - 14 - hc}" width="${bw * .4}" height="${hc}" fill="#e88a9a"><title>${x.strike}: call OI ${x.call_oi.toLocaleString("en-IN")}</title></rect><rect x="${x0 + bw * .5}" y="${H - 14 - hp}" width="${bw * .4}" height="${hp}" fill="#8fd0a8"><title>${x.strike}: put OI ${x.put_oi.toLocaleString("en-IN")}</title></rect>${i % 4 === 0 ? `<text x="${x0 + bw / 2}" y="${H - 3}" text-anchor="middle">${x.strike}</text>` : ""}${x.strike === d.atm ? `<line x1="${x0 + bw / 2}" x2="${x0 + bw / 2}" y1="6" y2="${H - 14}" stroke="#2563eb" stroke-dasharray="3 3"/>` : ""}${x.strike === d.max_pain ? `<line x1="${x0 + bw / 2}" x2="${x0 + bw / 2}" y1="6" y2="${H - 14}" stroke="#d97706" stroke-dasharray="3 3"/>` : ""}`; }).join("");
    const pcrNote = d.pcr == null ? "" : d.pcr >= 1.2 ? "more put than call open interest: traders lean protective or bullish" : d.pcr <= .7 ? "more call than put open interest: traders lean bullish or are capping the upside" : "roughly balanced";
    const oi = v => v == null ? "–" : (v >= 0 ? "+" : "") + Math.round(v / 1000).toLocaleString("en-IN") + "k";
    el.innerHTML = `<div class="lt"><div class="lt-card"><div class="lt-h"><b>OPTIONS · NEAREST EXPIRY ${esc(d.expiry)}</b><span class="src">${esc(d.source)} · ${esc(d.time || "")}</span></div>
      <div class="lt-grid">${kv("Put/call ratio (open interest)", num(d.pcr, 2))}${kv("Max pain", d.max_pain)}${kv("Underlying now", num(d.underlying, 2))}${kv("Biggest call wall (resistance)", d.call_walls[0] && d.call_walls[0].strike, "down")}${kv("Biggest put wall (support)", d.put_walls[0] && d.put_walls[0].strike, "up")}${kv("Open interest added today, calls / puts", `${oi(d.call_oi_change)} / ${oi(d.put_oi_change)}`)}${kv("At-the-money IV, call / put", d.atm_iv && d.atm_iv[0] != null ? `${num(d.atm_iv[0], 1)}% / ${num(d.atm_iv[1], 1)}%` : null)}</div>
      <div class="lt-ch" style="margin-top:8px"><h5><span>Open interest by strike</span><span class="muted"><span style="color:#dc3f54">calls</span> · <span style="color:#22a05a">puts</span> · <span style="color:#2563eb">now</span> · <span style="color:#d97706">max pain</span></span></h5><svg viewBox="0 0 ${W} ${H}" style="max-width:560px">${bars}</svg></div>
      <div class="note" style="margin-top:6px">PCR ${num(d.pcr, 2)}: ${pcrNote}. Large call open interest at a strike often acts as resistance, large put open interest as support, because sellers defend them. Max pain is the expiry price at which option buyers lose the most; price is sometimes drawn towards it near expiry, but that is a tendency, not a rule.</div></div></div>`;
  };
})();
