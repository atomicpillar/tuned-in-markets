/* Deep research view: turns the TradingAgents result into the same kind of cards, meters and tables as the rest of the app,
   and lets the reader save the whole report (a standalone page or plain Markdown) to their own computer. */
(() => {
  const esc = x => String(x ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const SCALE = ["SELL", "UNDERWEIGHT", "HOLD", "OVERWEIGHT", "BUY"];
  const COL = {BUY: "#2f9e5f", OVERWEIGHT: "#5cbf86", HOLD: "#b7791f", UNDERWEIGHT: "#e88a9a", SELL: "#d6455d"};
  const GROUP = k => (k === "BUY" || k === "OVERWEIGHT") ? "BUY" : (k === "SELL" || k === "UNDERWEIGHT") ? "SELL" : "HOLD";

  const CSS = `
.dr{font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#141a26}
.dr *{box-sizing:border-box}
.dr .top{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:2px 0 12px}
.dr .big{font-size:26px;font-weight:800;letter-spacing:.6px;padding:6px 16px;border-radius:10px;color:#fff}
.dr .meta{font-size:11.5px;color:#6b7385}.dr .meta b{color:#141a26}
.dr .acts{margin-left:auto;display:flex;gap:6px}
.dr .btn{border:1px solid #d9dee6;background:#fff;border-radius:8px;padding:6px 11px;font:600 11.5px inherit;font-family:inherit;cursor:pointer;color:#141a26}
.dr .btn:hover{border-color:#3b5bdb;color:#3b5bdb}
.dr .scale{position:relative;margin:4px 0 16px;padding-top:16px}
.dr .bar{display:grid;grid-template-columns:repeat(5,1fr);gap:3px}
.dr .bar i{height:8px;border-radius:4px;opacity:.28}.dr .bar i.on{opacity:1}
.dr .lab{display:grid;grid-template-columns:repeat(5,1fr);font-size:9.5px;letter-spacing:.5px;color:#6b7385;text-align:center;margin-top:4px;font-weight:700}
.dr .lab span.on{color:#141a26}
.dr .pin{position:absolute;top:0;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:9px solid #141a26;transform:translateX(-6px)}
.dr .card{border:1px solid #eef1f5;border-radius:10px;padding:11px 13px;background:#fff}
.dr .h{font-size:10px;color:#6b7385;letter-spacing:.7px;font-weight:700;margin:16px 0 7px;text-transform:uppercase}
.dr .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px}
.dr .grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:9px}
.dr .pill{display:inline-block;font-size:10.5px;font-weight:800;letter-spacing:.5px;padding:2px 9px;border-radius:99px;color:#fff}
.dr .nm{font-weight:700;font-size:12.5px;display:flex;justify-content:space-between;align-items:center;gap:6px}
.dr .tally{display:flex;height:14px;border-radius:7px;overflow:hidden;background:#eef1f5}
.dr .tally span{display:block;height:100%}
.dr .key{display:flex;gap:14px;font-size:11px;color:#6b7385;margin-top:6px;flex-wrap:wrap}.dr .key b{color:#141a26}
.dr .gauge{height:6px;border-radius:3px;background:linear-gradient(90deg,#d6455d,#e0b04a 50%,#2f9e5f);position:relative;margin:7px 0 2px}
.dr .gauge u{position:absolute;top:-4px;width:3px;height:14px;background:#141a26;border-radius:2px;text-decoration:none}
.dr details{margin-top:7px}.dr summary{cursor:pointer;font-size:11.5px;font-weight:600;color:#3b5bdb;list-style:none}.dr summary::-webkit-details-marker{display:none}
.dr summary:before{content:"+ "}.dr details[open]>summary:before{content:"- "}
.dr .md h1,.dr .md h2,.dr .md h3,.dr .md h4{margin:12px 0 4px;font-size:13px}.dr .md h1{font-size:15px}
.dr .md p{margin:5px 0}.dr .md ul,.dr .md ol{margin:5px 0;padding-left:20px}.dr .md li{margin:2px 0}
.dr .md hr{border:0;border-top:1px solid #eef1f5;margin:10px 0}
.dr .md code{background:#f1f3f6;border-radius:4px;padding:0 4px;font-size:11.5px}
.dr .tw{overflow-x:auto;margin:8px 0}
.dr table{border-collapse:collapse;font-size:11.5px;min-width:100%}
.dr th{background:#f6f8fa;text-align:left;font-size:10.5px;letter-spacing:.3px}
.dr th,.dr td{border:1px solid #e6eaf0;padding:4px 8px;vertical-align:top}
.dr .bull{border-top:3px solid #2f9e5f}.dr .bear{border-top:3px solid #d6455d}.dr .neu{border-top:3px solid #b7791f}.dr .plan{border-top:3px solid #3b5bdb}
.dr .clip{max-height:210px;overflow:hidden;position:relative}
.dr .clip:after{content:"";position:absolute;left:0;right:0;bottom:0;height:46px;background:linear-gradient(transparent,#fff)}
.dr .clip.full{max-height:none}.dr .clip.full:after{display:none}.dr .more{border:0;background:none;color:#3b5bdb;font:600 11.5px inherit;font-family:inherit;cursor:pointer;padding:4px 0 0}
.dr .foot{font-size:10.5px;color:#6b7385;margin-top:14px;line-height:1.5}
`;

  const inline = s => esc(s).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>").replace(/`([^`]+)`/g, "<code>$1</code>");
  // small markdown renderer: headings, lists, tables, rules, bold, italic, code
  function md(src) {
    const L = String(src || "").replace(/\r/g, "").split("\n"); let out = "", i = 0, list = null;
    const close = () => { if (list) { out += `</${list}>`; list = null; } };
    const cells = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
    while (i < L.length) {
      const l = L[i], t = l.trim();
      if (!t) { close(); i++; continue; }
      if (/^\|.*\|$/.test(t) && i + 1 < L.length && /^\|?\s*:?-{2,}/.test(L[i + 1].trim())) {
        close(); const head = cells(t); i += 2; const rows = [];
        while (i < L.length && /^\|.*\|$/.test(L[i].trim())) rows.push(cells(L[i++]));
        out += `<div class="tw"><table><tr>${head.map(c => `<th>${inline(c)}</th>`).join("")}</tr>${rows.map(r => `<tr>${r.map(c => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</table></div>`; continue;
      }
      let m;
      if ((m = t.match(/^(#{1,4})\s+(.*)$/))) { close(); out += `<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`; }
      else if (/^(-{3,}|\*{3,})$/.test(t)) { close(); out += "<hr>"; }
      else if ((m = t.match(/^[-*]\s+(.*)$/))) { if (list !== "ul") { close(); out += "<ul>"; list = "ul"; } out += `<li>${inline(m[1])}</li>`; }
      else if ((m = t.match(/^\d+[.)]\s+(.*)$/))) { if (list !== "ol") { close(); out += "<ol>"; list = "ol"; } out += `<li>${inline(m[1])}</li>`; }
      else if ((m = t.match(/^\*\*([^*]+?):?\*\*:?\s*$/))) { close(); out += `<h4>${inline(m[1])}</h4>`; }
      else { close(); out += `<p>${inline(t)}</p>`; }
      i++;
    }
    close(); return `<div class="md">${out}</div>`;
  }

  const stanceOf = text => {
    const m = String(text || "").match(/FINAL\s+(?:TRANSACTION\s+)?(?:PROPOSAL|RECOMMENDATION)\W*(BUY|HOLD|SELL|OVERWEIGHT|UNDERWEIGHT)/i)
      || String(text || "").match(/\*\*(?:Rating|Recommendation)\*\*:?\s*\**\s*(BUY|HOLD|SELL|OVERWEIGHT|UNDERWEIGHT)/i);
    return m ? m[1].toUpperCase() : null;
  };
  const scoreOf = text => { const m = String(text || "").match(/Score:?\s*(\d+(?:\.\d+)?)\s*\/\s*10/i); return m ? Math.max(0, Math.min(10, +m[1])) : null; };
  const pill = k => k ? `<span class="pill" style="background:${COL[k] || "#6b7385"}">${esc(k)}</span>` : "";

  function parts(d) {
    const rating = (stanceOf(d.final) || String(d.decision || "").toUpperCase().replace(/[^A-Z]/g, "")) || "HOLD";
    const R = SCALE.includes(rating) ? rating : "HOLD";
    return {R, idx: SCALE.indexOf(R)};
  }

  function body(d, live) {
    const {R, idx} = parts(d), sym = d.ticker || d.sym || "";
    const when = d.built ? new Date(d.built * 1000).toLocaleString() : "";
    const analysts = Object.entries(d.reports || {}).filter(([, v]) => v);
    const risk = Object.entries(d.risk || {}).filter(([, v]) => v);
    const votes = [];
    analysts.forEach(([k, v]) => { const s = stanceOf(v); if (s) votes.push(GROUP(s)); });
    const ps = stanceOf((d.plan || {})["Trader's plan"] || Object.values(d.plan || {})[0]); if (ps) votes.push(GROUP(ps));
    risk.forEach(([k, v]) => { const s = stanceOf(v); if (s) votes.push(GROUP(s)); });
    const cnt = {BUY: 0, HOLD: 0, SELL: 0}; votes.forEach(v => cnt[v]++);
    const tot = votes.length;
    const seg = k => cnt[k] ? `<span style="width:${cnt[k] / tot * 100}%;background:${COL[k]}"></span>` : "";
    const card = (cls, title, text, open) => text ? `<div class="card ${cls}"><div class="nm">${esc(title)}${pill(stanceOf(text))}</div><div class="clip">${md(text)}</div><button class="more">Show all</button></div>` : "";
    const sec = (title, inner) => inner ? `<div class="h">${esc(title)}</div>${inner}` : "";

    const scoreCards = analysts.map(([k, v]) => {
      const st = stanceOf(v), sc = scoreOf(v);
      return `<div class="card"><div class="nm">${esc(k.replace(/ analyst/i, ""))}${pill(st)}</div>${sc !== null ? `<div class="gauge"><u style="left:calc(${sc * 10}% - 1px)"></u></div><div class="meta">Sentiment score <b>${sc}/10</b></div>` : ""}<div class="clip">${md(v)}</div><button class="more">Show all</button></div>`;
    }).join("");

    const dbt = d.debate || {};
    const judgeKey = Object.keys(dbt).find(k => /manager|judge/i.test(k));
    const bull = Object.keys(dbt).find(k => /bull/i.test(k)), bear = Object.keys(dbt).find(k => /bear/i.test(k));
    const riskCls = k => /aggress/i.test(k) ? "bull" : /conserv/i.test(k) ? "bear" : /neutral/i.test(k) ? "neu" : "plan";
    const riskMain = risk.filter(([k]) => !/judge/i.test(k)), riskJudge = risk.find(([k]) => /judge/i.test(k));

    return `<div class="dr">
<div class="top"><div class="big" style="background:${COL[R]}">${esc(R)}</div>
 <div class="meta"><b style="font-size:15px">${esc(sym)}</b><br>Analysis for ${esc(d.date || "")}${when ? " · built " + esc(when) : ""}</div>
 ${live ? `<div class="acts"><button class="btn" data-dl="html">Download report</button><button class="btn" data-dl="md">Download as Markdown</button></div>` : ""}</div>
<div class="scale"><div class="pin" style="left:${idx * 20 + 10}%"></div><div class="bar">${SCALE.map((k, i) => `<i style="background:${COL[k]}" class="${i === idx ? "on" : ""}"></i>`).join("")}</div>
 <div class="lab">${SCALE.map((k, i) => `<span class="${i === idx ? "on" : ""}">${k}</span>`).join("")}</div></div>
${sec("The decision", `<div class="card">${md(d.final)}</div>`)}
${tot ? sec("Where the desk lands", `<div class="tally">${seg("BUY")}${seg("HOLD")}${seg("SELL")}</div><div class="key"><span><b>${cnt.BUY}</b> lean buy</span><span><b>${cnt.HOLD}</b> hold</span><span><b>${cnt.SELL}</b> lean sell</span><span>of ${tot} stated views across analysts, trader and risk team</span></div>`) : ""}
${sec("The four analysts", analysts.length ? `<div class="grid">${scoreCards}</div>` : "")}
${sec("Bull case against bear case", bull || bear ? `<div class="grid2">${card("bull", "Bull case", dbt[bull])}${card("bear", "Bear case", dbt[bear])}</div>` : "")}
${judgeKey ? sec("Research manager's ruling", `<div class="card plan">${md(dbt[judgeKey])}</div>`) : ""}
${sec("Trader's plan", Object.values(d.plan || {}).filter(Boolean).map(v => `<div class="card plan">${md(v)}</div>`).join(""))}
${sec("Risk team", riskMain.length ? `<div class="grid">${riskMain.map(([k, v]) => card(riskCls(k), k.replace(/ analyst/i, ""), v)).join("")}</div>` : "")}
${riskJudge ? sec("Risk judge", `<div class="card plan"><div class="clip">${md(riskJudge[1])}</div><button class="more">Show all</button></div>`) : ""}
<div class="foot">Written by AI agents from public data. It can be wrong, it is not advice, and it is not a recommendation to buy or sell. Check the numbers yourself before acting.</div>
</div>`;
  }

  function markdown(d) {
    const {R} = parts(d); const h = (t, o) => Object.entries(o || {}).filter(([, v]) => v).map(([k, v]) => `## ${t}: ${k}\n\n${v}\n`).join("\n");
    return `# ${d.ticker || ""} deep research, ${d.date || ""}\n\n**Decision: ${R}**\n\n${d.final || ""}\n\n${h("Analyst", d.reports)}\n${h("Debate", d.debate)}\n${h("Trader", d.plan)}\n${h("Risk", d.risk)}\n---\nWritten by AI agents from public data. Not advice.\n`;
  }
  function save(name, mime, text) {
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], {type: mime})); a.download = name;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  window.deepRender = {body, md, markdown, stanceOf};   // exposed for testing

  let DT = null;
  window.deepBox = (el, sym) => {
    clearTimeout(DT);
    if (!el) return;
    if (!sym || window.MK.idxSet.includes(sym) || String(sym).startsWith("^")) { el.innerHTML = ""; return; }
    const shell = inner => { el.innerHTML = `<style>${CSS}</style><div class="rp"><div class="rp-card" style="margin-top:12px"><div class="h" style="margin-top:0">DEEP RESEARCH</div>${inner}</div></div>`; };
    const draw = async () => {
      let d; try { d = await (await fetch(`/api/deep?sym=${encodeURIComponent(sym)}`)).json(); } catch (e) { return; }
      if (el.dataset.sym !== sym) return;
      if (d.state === "setup") shell(`<div class="muted" style="font-size:12px">${esc(d.why)} Setup takes a few minutes, once: see docs/DEEP-RESEARCH.md.</div>`);
      else if (d.state === "none") {
        shell(`<div style="font-size:12px;color:#44506a;line-height:1.5">A team of AI analysts reads the news, the numbers and the chart for ${esc(sym)}, argues the bull and bear case, and writes a decision with reasons. It runs on your own OpenAI key and costs a few cents to about fifteen cents per stock. It takes 5 to 15 minutes.</div><button id="deepgo" class="dr-go" style="margin-top:9px;border:0;background:#3b5bdb;color:#fff;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer">Run deep research on ${esc(sym)}</button>`);
        const b = el.querySelector("#deepgo"); b.onclick = async () => { b.disabled = true; await fetch(`/api/deep?sym=${encodeURIComponent(sym)}&action=start`); draw(); };
      } else if (d.state === "running") {
        shell(`<div class="muted" style="font-size:12px"><span class="rp-spin"></span> The analysts are working (${Math.floor((d.elapsed || 0) / 60)} min ${(d.elapsed || 0) % 60} s). You can close this window: the result is kept.</div>`);
        DT = setTimeout(draw, 5000);
      } else if (d.state === "error") shell(`<div class="down" style="font-size:12px">It did not finish: ${esc(d.error || "unknown error")}</div><div class="muted" style="font-size:11px;margin-top:4px;white-space:pre-wrap">${esc(d.trace || "")}</div>`);
      else if (d.state === "done") {
        shell(body(d, true));
        el.querySelectorAll(".more").forEach(b => { const c = b.previousElementSibling; if (c.scrollHeight <= c.clientHeight + 4) { b.remove(); c.classList.add("full"); } else b.onclick = () => { const f = c.classList.toggle("full"); b.textContent = f ? "Show less" : "Show all"; }; });
        const base = `${sym}-deep-research-${d.date || "report"}`;
        el.querySelectorAll("[data-dl]").forEach(b => b.onclick = () => {
          if (b.dataset.dl === "md") save(base + ".md", "text/markdown", markdown(d));
          else save(base + ".html", "text/html", `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(base)}</title><style>body{margin:0;background:#edf0f3}.page{max-width:980px;margin:0 auto;padding:22px 18px;background:#fff}${CSS}.dr .clip{max-height:none}.dr .clip:after{display:none}.dr .more{display:none}</style></head><body><div class="page">${body(d, false)}</div></body></html>`);
        });
      }
    };
    el.dataset.sym = sym; draw();
  };
})();
