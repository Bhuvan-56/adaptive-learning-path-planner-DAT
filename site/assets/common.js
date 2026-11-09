// Shared helpers: header/nav, JSON fetch, source labels, small SVG + tooltip utilities.
// Paths are relative to site/; repository files live one level up ("../").
(function () {
  const PAGES = [
    ["index.html", "Overview"],
    ["curriculum.html", "Curriculum"],
    ["scheduling.html", "Scheduling"],
    ["results.html", "Results"],
    ["demos.html", "Live demos"],
  ];

  // Theme: follows the system unless the visitor picks one (remembered per browser when storage works).
  function storedTheme() { try { return localStorage.getItem("theme"); } catch (e) { return null; } }
  function applyTheme(t) {
    if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
    else document.documentElement.removeAttribute("data-theme");
  }
  applyTheme(storedTheme());
  function currentTheme() {
    const t = document.documentElement.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function header() {
    const here = location.pathname.split("/").pop() || "index.html";
    const nav = PAGES.map(([href, label]) =>
      `<a href="${href}"${href === here ? ' class="active" aria-current="page"' : ""}>${label}</a>`).join("");
    const h = document.createElement("header");
    h.className = "site";
    h.innerHTML = `<div class="inner"><a class="brand" href="index.html"><span class="logo" aria-hidden="true"></span>Adaptive Learning-Path Planner</a>
      <nav>${nav}</nav><button class="theme-toggle" type="button" aria-label="Switch light or dark theme" title="Switch theme"></button></div>`;
    document.body.prepend(h);
    const btn = h.querySelector(".theme-toggle");
    const label = () => { btn.textContent = currentTheme() === "dark" ? "☀" : "☾"; };
    label();
    btn.addEventListener("click", () => {
      const next = currentTheme() === "dark" ? "light" : "dark";
      applyTheme(next);
      try { localStorage.setItem("theme", next); } catch (e) { /* storage blocked: theme lasts for this page */ }
      label();
    });
    const f = document.createElement("footer");
    f.innerHTML = `Made by Bhuvan Chandra and Abdur Rehman &middot; CS5903 &middot; Week 7 and Week 8 results &middot; every number comes from a simulator with synthetic learners`;
    document.body.append(f);
  }

  // ---------------------------------------------------------------------------
  // Layered drawing of a prerequisite DAG, top to bottom.
  // nodes: [{id, name, minutes}], edges: [[source, target], ...]
  // opts.style(id) -> {fill, opacity, dashed, strong, dim, badge}; opts.tip(id) -> html; opts.label
  // Layer (row) = longest path from a root; boxes in a layer ordered by the mean
  // position of their neighbours (a few sweeps) to reduce crossings. Returns an SVG string.
  function dagSVG(nodes, edges, opts = {}) {
    const ids = nodes.map(n => n.id), byId = Object.fromEntries(nodes.map(n => [n.id, n]));
    const preds = Object.fromEntries(ids.map(i => [i, []])), succs = Object.fromEntries(ids.map(i => [i, []]));
    edges.forEach(([a, b]) => { preds[b].push(a); succs[a].push(b); });
    const col = {};
    const depth = id => col[id] ?? (col[id] = preds[id].length ? 1 + Math.max(...preds[id].map(depth)) : 0);
    ids.forEach(depth);
    const C = Math.max(...Object.values(col)) + 1;
    const cols = Array.from({ length: C }, (_, c) => ids.filter(i => col[i] === c));
    const row = {};
    cols.forEach(cs => cs.forEach((id, r) => row[id] = r));
    const mean = (xs, d) => xs.length ? xs.reduce((t, x) => t + row[x], 0) / xs.length : d;
    for (let sweep = 0; sweep < 4; sweep++) {
      const back = sweep % 2 === 1;
      const order = back ? [...cols].reverse() : cols;
      order.forEach(cs => {
        const key = Object.fromEntries(cs.map(id => [id, mean(back ? succs[id] : preds[id], row[id])]));
        cs.sort((a, b) => key[a] - key[b] || a.localeCompare(b));
        cs.forEach((id, r) => row[id] = r);
      });
    }
    const R = Math.max(...cols.map(c => c.length));
    const BW = opts.boxW || 164, BH = 48, GX = 16, GY = 40, PAD = 12;
    const W = PAD * 2 + R * BW + (R - 1) * GX, H = PAD * 2 + C * BH + (C - 1) * GY;
    const pos = {};
    cols.forEach((cs, c) => {
      const off = (R - cs.length) * (BW + GX) / 2;
      cs.forEach((id, r) => pos[id] = { x: PAD + off + r * (BW + GX), y: PAD + c * (BH + GY) });
    });
    const st = id => (opts.style ? opts.style(id) : {}) || {};
    const uid = "m" + Math.random().toString(36).slice(2, 8);
    let svg = `<svg class="chart dag" viewBox="0 0 ${W} ${H}" style="min-width:${Math.round(W * 0.7)}px;max-width:${W}px" role="img" aria-label="${esc(opts.label || "Prerequisite graph")}">
      <defs><marker id="${uid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="var(--edge)"/></marker></defs>`;
    edges.forEach(([a, b]) => {
      const p = pos[a], q = pos[b];
      const x1 = p.x + BW / 2, y1 = p.y + BH, x2 = q.x + BW / 2, y2 = q.y - 2, my = (y1 + y2) / 2;
      const dim = (st(a).dim || st(b).dim) ? ' opacity="0.25"' : "";
      svg += `<path d="M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}" fill="none" stroke="var(--edge)" stroke-width="1.4" marker-end="url(#${uid})"${dim}/>`;
    });
    ids.forEach(id => {
      const n = byId[id], p = pos[id], s = st(id);
      const tip = opts.tip ? opts.tip(id) : `<b>${esc(id)}</b>: ${esc(n.name)}<br>${n.minutes} min`;
      const name = n.name.length > 26 ? n.name.slice(0, 25) + "…" : n.name;
      svg += `<g class="dag-node${s.dim ? " dim" : ""}" data-node="${esc(id)}" data-tip="${esc(tip)}" tabindex="0">
        <rect x="${p.x}" y="${p.y}" width="${BW}" height="${BH}" rx="9" fill="var(--surface)" stroke="${s.strong ? "var(--text)" : "var(--border-strong)"}" stroke-width="${s.strong ? 2.2 : 1.2}"${s.dashed ? ' stroke-dasharray="4 3"' : ""}/>
        ${s.fill ? `<rect x="${p.x}" y="${p.y}" width="${BW}" height="${BH}" rx="9" fill="${s.fill}" fill-opacity="${s.opacity ?? 1}" pointer-events="none"/>` : ""}
        <text x="${p.x + 10}" y="${p.y + 20}" class="dag-id">${esc(id)}</text>
        <text x="${p.x + BW - 10}" y="${p.y + 20}" text-anchor="end" class="dag-min">${esc(s.badge ?? n.minutes + " min")}</text>
        <text x="${p.x + 10}" y="${p.y + 38}" class="dag-name">${esc(name)}</text></g>`;
    });
    return svg + "</svg>";
  }

  // All prerequisites of id, direct or not.
  function ancestors(id, edges) {
    const out = new Set(), stack = [id];
    while (stack.length) {
      const x = stack.pop();
      edges.forEach(([a, b]) => { if (b === x && !out.has(a)) { out.add(a); stack.push(a); } });
    }
    return out;
  }

  async function getJSON(path) {
    const r = await fetch(path, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.json();
  }

  async function getText(path) {
    const r = await fetch(path, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.text();
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // "Source: path" line; paths are repo-relative and link to the file served next to the site.
  function src(paths, extra) {
    const list = (Array.isArray(paths) ? paths : [paths])
      .map(p => `<a href="../${p}"><code>${esc(p)}</code></a>`).join(", ");
    return `<span class="src">Source: ${list}${extra ? " &middot; " + extra : ""}</span>`;
  }

  function fmt4(x) { return Number(x).toFixed(4); }
  function signed4(x) { const v = Number(x); return (v > 0 ? "+" : "") + v.toFixed(4); }

  // one tooltip element shared by every chart
  let tip;
  function tooltip() {
    if (!tip) { tip = document.createElement("div"); tip.className = "tooltip"; document.body.append(tip); }
    return tip;
  }
  function bindTips(root) {
    root.querySelectorAll("[data-tip]").forEach(el => {
      const show = e => {
        const t = tooltip(); t.innerHTML = el.getAttribute("data-tip"); t.style.display = "block";
        const x = (e.touches ? e.touches[0].clientX : e.clientX), y = (e.touches ? e.touches[0].clientY : e.clientY);
        const w = t.offsetWidth;
        t.style.left = Math.min(window.innerWidth - w - 8, x + 12) + "px";
        t.style.top = (y + 14) + "px";
      };
      el.addEventListener("mousemove", show);
      el.addEventListener("touchstart", show, { passive: true });
      el.addEventListener("mouseleave", () => { tooltip().style.display = "none"; });
    });
  }

  function fail(el, err) {
    el.innerHTML = `<p class="err">Could not load data: ${esc(err.message || err)}.</p>
      <p class="small">Serve the repository root with <code>python -m http.server</code> and open <code>/site/</code>; pages read files with fetch(), which does not work from file://.</p>`;
  }

  window.Site = { header, getJSON, getText, esc, src, fmt4, signed4, bindTips, fail, dagSVG, ancestors };
  document.addEventListener("DOMContentLoaded", header);
})();
