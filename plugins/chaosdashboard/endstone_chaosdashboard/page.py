PAGE = r"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chaos Dashboard</title>
<style>
:root {
  --bg:#1a1a1a; --side:#141414; --panel:#161616; --panel-alt:#1c1c1c; --line:#2a2a2a; --side-line:#262626;
  --text:#f3f4f6; --muted:#9ca3af; --green:#22c55e; --red:#f87171; --gold:#fbbf24;
  --outline:#1e1e1f; --font:Inter,"Segoe UI",system-ui,sans-serif; --mono:"JetBrains Mono",Consolas,monospace;
}
* { box-sizing:border-box; }
html, body { margin:0; height:100%; }
body { background:var(--bg); color:var(--text); font:15px/1.5 var(--font); }
h1, h2 { margin:0; font-weight:700; }
button, input, select { font:inherit; color:inherit; }
:focus-visible { outline:2px solid var(--green); outline-offset:2px; }
.shell { display:grid; grid-template-columns:232px minmax(0,1fr); min-height:100vh; }
.side { position:sticky; top:0; height:100vh; background:var(--side); border-right:1px solid var(--side-line); display:flex; flex-direction:column; }
.brand { padding:18px 20px; border-bottom:1px solid var(--side-line); }
.brand strong { display:block; overflow-wrap:anywhere; }
.brand span { color:var(--muted); font:500 12px var(--mono); }
nav { padding:10px 0; display:flex; flex-direction:column; }
nav button { all:unset; box-sizing:border-box; cursor:pointer; padding:10px 20px; border-left:3px solid transparent; color:var(--muted); display:flex; justify-content:space-between; gap:12px; font-weight:600; }
nav button:hover { color:var(--text); background:var(--panel-alt); }
nav button:focus-visible { outline:2px solid var(--green); outline-offset:-2px; }
nav button[aria-current=page] { color:var(--text); border-left-color:var(--green); background:var(--panel-alt); }
nav .count { font:500 12px var(--mono); }
.status { margin-top:auto; padding:14px 20px; border-top:1px solid var(--side-line); color:var(--muted); font:500 12px var(--mono); }
.status b { color:var(--green); font-weight:600; }
.status.off b { color:var(--red); }
.view { padding:28px 32px; max-width:1040px; }
.head { display:flex; justify-content:space-between; align-items:baseline; gap:16px; margin-bottom:18px; flex-wrap:wrap; }
.head h1 { font-size:22px; }
.head span { color:var(--muted); }
.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); border:1px solid var(--line); background:var(--panel); margin-bottom:24px; }
.stat { padding:14px 16px; border-right:1px solid var(--line); text-align:left; background:none; border-top:0; border-bottom:0; border-left:0; cursor:pointer; }
.stat:last-child { border-right:0; }
.stat:hover { background:var(--panel-alt); }
.stat b { display:block; font:600 26px var(--mono); }
.stat span { color:var(--muted); font-size:13px; }
.table { border:1px solid var(--line); background:var(--panel); }
.row { display:flex; gap:16px; align-items:center; justify-content:space-between; padding:10px 14px; border-top:1px solid var(--line); flex-wrap:wrap; }
.row:first-child { border-top:0; }
.who { min-width:0; flex:1 1 220px; }
.who b { display:block; font-weight:600; overflow-wrap:anywhere; white-space:pre-wrap; }
.who span { color:var(--muted); font:500 12px var(--mono); overflow-wrap:anywhere; }
.act { display:flex; gap:8px; align-items:center; }
.none { padding:18px 14px; color:var(--muted); }
.btn { border:2px solid var(--outline); border-radius:2px; padding:6px 12px 8px; font-weight:700; font-size:13px; cursor:pointer; color:#fff; background:#1d4d13; box-shadow:inset 2px 2px 0 #316823, inset -2px -3px 0 #3c8527; }
.btn:hover { background:#245d19; }
.btn:active { box-shadow:inset 2px 2px 0 var(--outline); }
.btn.grey { background:#c0c1c4; color:#313233; box-shadow:inset 2px 2px 0 #edeeef, inset -2px -3px 0 #6a6c70; }
.btn.grey:hover { background:#c9cbcd; }
.btn.bad { background:#8f1d1d; box-shadow:inset 2px 2px 0 #b83232, inset -2px -3px 0 #6e1414; }
.btn.bad:hover { background:#a02323; }
input, select { background:#101010; border:1px solid var(--line); border-radius:2px; padding:7px 10px; min-width:0; }
input { flex:1; font-family:var(--mono); font-size:14px; }
input:focus, select:focus { border-color:var(--green); outline:0; }
.line { display:flex; gap:8px; }
.log { margin-top:14px; border:1px solid var(--line); background:#101010; padding:10px 12px; min-height:120px; font:500 13px/1.7 var(--mono); color:var(--muted); overflow-wrap:anywhere; }
.log b { color:var(--green); font-weight:500; }
.log i { color:var(--red); font-style:normal; }
.hint { color:var(--muted); font-size:13px; margin:10px 0 0; }
.login { min-height:100vh; display:grid; place-items:center; padding:16px; }
.login form { width:min(380px,100%); border:1px solid var(--line); background:var(--panel); padding:20px; }
.login h1 { font-size:18px; margin-bottom:4px; }
.login p { color:var(--muted); margin:0 0 14px; font-size:14px; }
#toast { position:fixed; right:16px; bottom:16px; background:var(--panel-alt); border:1px solid var(--line); border-left:3px solid var(--green); padding:9px 14px; display:none; max-width:calc(100vw - 32px); z-index:5; }
#toast.bad { border-left-color:var(--red); }
[hidden] { display:none !important; }
@media (max-width:760px) {
  .shell { grid-template-columns:minmax(0,1fr); }
  .side { position:static; height:auto; border-right:0; border-bottom:1px solid var(--side-line); }
  .brand { padding:12px 16px; }
  nav { flex-direction:row; overflow-x:auto; padding:0; scrollbar-width:none; flex:none; }
  nav button { border-left:0; border-bottom:3px solid transparent; padding:10px 14px; white-space:nowrap; }
  nav button[aria-current=page] { border-bottom-color:var(--green); }
  .status { display:none; }
  .view { padding:20px 16px; }
  .stat { border-bottom:1px solid var(--line); }
}
</style>
</head>
<body>
<div id="login" class="login" hidden>
  <form id="loginForm"><h1>Chaos Dashboard</h1><p>Das Passwort steht in settings.json des Plugins.</p>
  <div class="line"><input id="token" type="password" placeholder="Passwort" aria-label="Passwort" autocomplete="current-password"><button class="btn">Öffnen</button></div></form>
</div>
<div id="app" class="shell" hidden>
  <aside class="side">
    <div class="brand"><strong id="name">Server</strong><span id="version"></span></div>
    <nav id="nav" aria-label="Bereiche"></nav>
    <div class="status" id="status"><b>online</b></div>
  </aside>
  <main class="view"><div class="head"><h1 id="heading"></h1><span id="sub"></span></div><div id="content"></div></main>
</div>
<div id="toast" role="status"></div>
<script>
const views = [["home","Übersicht"],["players","Spieler"],["texts","Texte"],["portals","Portale"],["ranks","Ränge"],["console","Konsole"]];
let token = ""; let state = null; let view = "home"; const log = []; let toastTimer;
try { token = sessionStorage.getItem("token") || ""; } catch (e) {}
const $ = id => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const clean = text => text.replace(/§./g, "");
function toast(message, bad) { const t = $("toast"); t.textContent = message; t.className = bad ? "bad" : ""; t.style.display = "block"; clearTimeout(toastTimer); toastTimer = setTimeout(() => t.style.display = "none", 3500); }
async function api(path, body) {
  const response = await fetch(path, { method: body ? "POST" : "GET", headers: { "X-Token": token, "Content-Type": "application/json" }, body: body && JSON.stringify(body) });
  const data = await response.json();
  if (response.status === 401) { showLogin(); throw new Error(data.error); }
  if (!response.ok) throw new Error(data.error);
  return data;
}
async function act(body, label) {
  try { const r = await api("/api/action", body); toast(r.result); if (label) log.unshift(["ok", label]); }
  catch (error) { toast(error.message, true); if (label) log.unshift(["bad", label + " - " + error.message]); }
  if (view === "console") render();
  setTimeout(refresh, 1000);
}
function button(text, cls, onClick) { const b = el("button", "btn " + (cls || ""), text); b.type = "button"; b.onclick = onClick; return b; }
function row(title, detail, ...controls) {
  const r = el("div", "row"), who = el("div", "who"); who.append(el("b", "", title)); if (detail) who.append(el("span", "", detail));
  const a = el("div", "act"); a.append(...controls); r.append(who, a); return r;
}
function table(rows, emptyText) { const t = el("div", "table"); if (rows.length) t.append(...rows); else t.append(el("div", "none", emptyText)); return t; }
function missing(name) { return el("div", "table").appendChild(el("div", "none", name + " ist auf diesem Server nicht installiert.")).parentNode; }
function counts(s) { return { players: s.players.length, texts: s.texts ? Object.keys(s.texts).length : 0, portals: s.portals ? Object.keys(s.portals).length : 0, ranks: s.ranks ? Object.keys(s.ranks).length : 0 }; }
function playerRows(s) {
  return s.players.map(p => {
    const controls = [];
    if (s.ranks) {
      const select = el("select"); select.setAttribute("aria-label", "Rang von " + p.name);
      Object.keys(s.ranks).forEach(g => select.add(new Option(g, g, false, g === p.rank)));
      select.onchange = () => act({ type: "rank", player: p.name, rank: select.value });
      controls.push(select);
    }
    controls.push(button("Kicken", "bad", () => act({ type: "kick", player: p.name })));
    return row(p.name, p.dimension, ...controls);
  });
}
const pages = {
  home(s) {
    const c = counts(s), box = el("div"), stats = el("div", "stats");
    [["players","Spieler online"],["texts","Texte"],["portals","Portale"],["ranks","Ränge"]].forEach(([key, label]) => {
      const b = el("button", "stat"); b.type = "button"; b.append(el("b", "", c[key]), el("span", "", label)); b.onclick = () => go(key); stats.append(b);
    });
    box.append(stats, table(playerRows(s), "Gerade ist niemand online."));
    return box;
  },
  players: s => table(playerRows(s), "Gerade ist niemand online."),
  texts(s) {
    if (s.texts === null) return missing("ChaosTexts");
    return table(Object.entries(s.texts).map(([id, t]) => row(clean(t.text), id + "  " + t.dim + "  " + [t.x, t.y, t.z].map(Math.round).join(" / "), button("Entfernen", "bad", () => act({ type: "text_remove", id })))), "Noch keine Texte. Erstelle einen im Spiel mit /ft create.");
  },
  portals(s) {
    if (s.portals === null) return missing("ChaosPortals");
    return table(Object.entries(s.portals).map(([name, p]) => {
      const target = !p.target ? "kein Ziel" : p.target.type === "server" ? p.target.host + ":" + p.target.port : p.target.dim;
      return row(name, target + "  " + (p.signs || []).length + " Schilder", button("Entfernen", "bad", () => act({ type: "portal_remove", name })));
    }), "Noch keine Portale. Erstelle eins im Spiel mit /portal create.");
  },
  ranks(s) {
    if (s.ranks === null) return missing("ChaosRanks");
    return table(Object.entries(s.ranks).map(([name, g]) => {
      const members = Object.entries(s.assigned || {}).filter(([, r]) => r === name).map(([p]) => p);
      const parts = [Object.keys(g.perms).length + " Rechte"]; if (g.inherit.length) parts.push("erbt " + g.inherit.join(", ")); if (members.length) parts.push(members.join(", "));
      return row(name + (name === s.default_rank ? " (Standard)" : ""), parts.join("  "));
    }), "Keine Ränge.");
  },
  console() {
    const box = el("div"), form = el("form", "line"), input = el("input"), output = el("div", "log");
    input.placeholder = "allowlist add Gamertag"; input.setAttribute("aria-label", "Konsolenbefehl"); input.autocomplete = "off";
    form.append(input, el("button", "btn", "Senden"));
    form.onsubmit = e => { e.preventDefault(); const line = input.value.trim().replace(/^\//, ""); if (line) { input.value = ""; act({ type: "command", line }, line); } };
    if (log.length) log.slice(0, 40).forEach(([kind, text]) => { const d = el("div"); d.append(el(kind === "ok" ? "b" : "i", "", (kind === "ok" ? "> " : "! ") + text)); output.append(d); });
    else output.textContent = "Noch keine Befehle gesendet.";
    box.append(form, output, el("p", "hint", "Die Ausgabe eines Befehls steht im Server-Log."));
    return box;
  },
};
function render() {
  const s = state; if (!s) return;
  $("name").textContent = s.name; $("version").textContent = "Bedrock " + s.version;
  const c = counts(s), nav = $("nav");
  nav.replaceChildren(...views.map(([key, label]) => {
    const b = el("button"); b.type = "button"; b.append(el("span", "", label)); if (key in c) b.append(el("span", "count", c[key]));
    if (key === view) b.setAttribute("aria-current", "page"); b.onclick = () => go(key); return b;
  }));
  $("heading").textContent = views.find(([key]) => key === view)[1];
  const content = $("content"), typing = document.activeElement && document.activeElement.tagName;
  if (view === "console" && content.firstChild && typing === "INPUT" && !render.force) return;
  if (typing === "SELECT") return;
  content.replaceChildren(pages[view](s));
}
function go(key) { view = key; try { location.hash = key; } catch (e) {} render.force = true; render(); render.force = false; }
async function refresh() {
  try { state = (await api("/api/state")); $("status").className = "status"; $("status").firstChild.textContent = "online"; render(); }
  catch (error) { $("status").className = "status off"; $("status").firstChild.textContent = "keine Verbindung"; }
}
function showLogin() { $("app").hidden = true; $("login").hidden = false; $("token").focus(); }
async function open() {
  try { state = await api("/api/state"); $("login").hidden = true; $("app").hidden = false; try { sessionStorage.setItem("token", token); } catch (e) {} const h = location.hash.slice(1); if (views.some(([k]) => k === h)) view = h; render(); }
  catch (error) { showLogin(); if (token) toast(error.message, true); }
}
$("loginForm").onsubmit = e => { e.preventDefault(); token = $("token").value; open(); };
open(); setInterval(() => { if (!$("app").hidden) refresh(); }, 3000);
</script>
</body>
</html>
"""
