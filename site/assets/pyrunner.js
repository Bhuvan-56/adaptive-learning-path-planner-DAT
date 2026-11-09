// Starts Pyodide (pinned), copies the project's own Python files into its file system,
// imports site/py/demo_api.py, and exposes Engine.call(name, payload).
// If Pyodide cannot start (offline, CDN blocked, timeout), Engine.mode becomes "fallback"
// and pages show the saved outputs in data/fallback.json instead.
(function () {
  const PYODIDE_VERSION = "0.26.4";
  const INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
  const PACKAGES = ["networkx", "pyyaml"];
  const START_TIMEOUT_MS = 90000;

  // Repository files the demos need, relative to the repository root.
  // None of these starts with "_" (Jekyll on GitHub Pages skips such paths),
  // and none of the src/ folders used here has or needs an __init__.py.
  const FILES = [
    "src/curriculum/errors.py",
    "src/curriculum/graph.py",
    "src/state/policy.py",
    "src/state/learner_state.py",
    "src/trace/schema.py",
    "src/trace/universe.py",
    "src/trace/checker.py",
    "src/planning/admissibility.py",
    "src/planning/greedy.py",
    "src/planning/greedy_fallback.py",
    "src/planning/oracle.py",
    "src/planning/feasibility.py",
    "src/planning/static_baseline.py",
    "src/planning/service.py",
    "src/planning/difficulty.py",
    "src/planning/review.py",
    "src/planning/replan.py",
    "data/curricula/demo_curriculum.json",
    "data/curricula/maths_curriculum.json",
    "config/adaptive.yaml",
    "experiments/m8_learner_eval.yaml",
  ];

  const listeners = [];
  const Engine = {
    mode: "loading", // loading | ready | fallback
    detail: "",
    py: null,
    api: null,
    fallback: null,
    onChange(fn) { listeners.push(fn); fn(Engine); },
    async call(name, payload) {
      if (Engine.mode !== "ready") throw new Error("Python engine not ready");
      const out = Engine.api.call(name, JSON.stringify(payload || {}));
      return JSON.parse(out);
    },
  };
  function set(mode, detail) { Engine.mode = mode; Engine.detail = detail; listeners.forEach(f => f(Engine)); }

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = src; s.crossOrigin = "anonymous";
      s.onload = res; s.onerror = () => rej(new Error("could not load " + src));
      document.head.append(s);
    });
  }

  async function fetchText(path) {
    const r = await fetch(path, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.text();
  }

  async function start() {
    const t0 = performance.now();
    set("loading", "Downloading Python (Pyodide " + PYODIDE_VERSION + ")…");
    await loadScript(INDEX_URL + "pyodide.js");
    const py = await loadPyodide({ indexURL: INDEX_URL });
    set("loading", "Loading networkx and PyYAML…");
    await py.loadPackage(PACKAGES);
    set("loading", "Copying project code (src/) into the browser…");
    const files = FILES.concat(["site/py/demo_api.py"]);
    const texts = await Promise.all(files.map(f => fetchText("../" + f)));
    const root = "/home/pyodide/";
    files.forEach((f, i) => {
      const target = f === "site/py/demo_api.py" ? root + "demo_api.py" : root + f;
      const dir = target.slice(0, target.lastIndexOf("/"));
      py.FS.mkdirTree(dir);
      py.FS.writeFile(target, texts[i]);
    });
    set("loading", "Importing src.planning, src.state, src.curriculum, src.trace…");
    await py.runPythonAsync(`
import os, sys
os.chdir("/home/pyodide")
if "/home/pyodide" not in sys.path:
    sys.path.insert(0, "/home/pyodide")
import demo_api
`);
    Engine.py = py;
    Engine.api = py.globals.get("demo_api");
    const secs = ((performance.now() - t0) / 1000).toFixed(1);
    set("ready", `Live: project Python code running in your browser (Pyodide ${PYODIDE_VERSION}, ready in ${secs} s).`);
  }

  async function loadFallback() {
    try { Engine.fallback = await (await fetch("data/fallback.json", { cache: "no-cache" })).json(); } catch (e) { Engine.fallback = null; }
  }

  Engine.ready = (async () => {
    await loadFallback();
    const forceFallback = new URLSearchParams(location.search).has("fallback");
    try {
      if (forceFallback) throw new Error("fallback requested in the URL (?fallback)");
      await Promise.race([
        start(),
        new Promise((_, rej) => setTimeout(() => rej(new Error("timed out after " + START_TIMEOUT_MS / 1000 + " s")), START_TIMEOUT_MS)),
      ]);
    } catch (e) {
      console.error(e);
      set("fallback", "Python engine unavailable (" + e.message + "). Showing saved outputs of the presets, produced by the same code with site/build_data.py.");
    }
    return Engine;
  })();

  window.Engine = Engine;
})();
