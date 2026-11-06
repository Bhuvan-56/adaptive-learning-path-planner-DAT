// Shared helpers: header/nav, JSON fetch, source labels, small SVG + tooltip utilities.
// Paths are relative to site/; repository files live one level up ("../").
(function () {
  const PAGES = [
    ["index.html", "Overview"],
    ["curriculum.html", "Curriculum"],
    ["scheduling.html", "Scheduling"],
    ["results.html", "Integrated S0"],
    ["demos.html", "Live demos"],
  ];

  function header() {
    const here = location.pathname.split("/").pop() || "index.html";
    const nav = PAGES.map(([href, label]) =>
      `<a href="${href}"${href === here ? ' class="active" aria-current="page"' : ""}>${label}</a>`).join("");
    const h = document.createElement("header");
    h.className = "site";
    h.innerHTML = `<div class="inner"><a class="brand" href="index.html">Adaptive Learning-Path Planner</a><nav>${nav}</nav></div>`;
    document.body.prepend(h);
    const f = document.createElement("footer");
    f.innerHTML = `Made by: Bhuvan and Abdur &middot; Week 7 results &middot; numbers come from a simulator with synthetic learners`;
    document.body.append(f);
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

  window.Site = { header, getJSON, getText, esc, src, fmt4, signed4, bindTips, fail };
  document.addEventListener("DOMContentLoaded", header);
})();
