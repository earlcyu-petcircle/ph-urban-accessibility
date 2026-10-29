#!/usr/bin/env python3
"""
Step 6: the interactive map, docs/index.html.

One self-contained page: Leaflet from a CDN, the barangay scores and the outlines
of the three places lived inlined as GeoJSON. Open it in a browser, or serve docs/
with GitHub Pages. Hover (or tap) a barangay for its scores; the selector switches
the colouring between the composite and each service.
"""
import json

from common import (ACCENT, BG, DERIVED, DOCS, FAINT, INK, MUTED, OVERTURE_RELEASE, RULE, SCORE_BREAKS,
                    SCORE_COLOURS, SERVICE_LABELS, SURFACE)

barangays = json.loads((DERIVED / "barangay_scores.geojson").read_text())
lived = json.loads((DERIVED / "places_lived.geojson").read_text())
headline = json.loads((DERIVED / "headline.json").read_text())
for g in (barangays, lived):
    g.pop("name", None)
    g.pop("crs", None)

page = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Metro Manila Walking Access</title>
<meta name="description" content="Walking access to groceries, healthcare, parks, transit and schools for every barangay in Metro Manila, scored 0-100.">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Karla:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  color-scheme: light;
  --bg:__BG__; --surface:__SURFACE__; --ink:__INK__; --muted:__MUTED__; --faint:__FAINT__;
  --rule:#D9CFBA; --rule-strong:__RULE__; --accent:__ACCENT__; --accent-tint:#EADFC5;
  --serif:"Newsreader", Georgia, "Times New Roman", serif;
  --sans:"Karla", system-ui, -apple-system, sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, Menlo, monospace;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5}
#app{display:grid;grid-template-columns:minmax(300px,380px) 1fr;height:100%}
#side{overflow-y:auto;padding:22px 22px 18px;border-right:1px solid var(--rule-strong);background:var(--bg)}
#map{height:100%;background:#E9E3D4}
.kicker{font-size:.72rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--accent)}
h1{font-family:var(--serif);font-weight:500;font-size:1.85rem;line-height:1.1;margin:.3rem 0 .5rem;text-wrap:balance}
h1 em{font-style:italic}
.lead{font-family:var(--serif);font-size:1.02rem;line-height:1.45;color:var(--muted);margin:0 0 .9rem}
h2{font-family:var(--serif);font-weight:600;font-size:1.05rem;margin:1.1rem 0 .45rem;padding-bottom:.2rem;border-bottom:3px double var(--rule-strong)}
.sel{display:flex;flex-wrap:wrap;gap:6px}
.sel button{font:500 .85rem var(--sans);color:var(--ink);background:var(--surface);border:1px solid var(--rule-strong);border-radius:3px;padding:5px 9px;cursor:pointer}
.sel button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.legend{display:flex;margin-top:9px}
.legend span{flex:1;height:12px}
.legend-l{display:flex;justify-content:space-between;font:.72rem var(--mono);color:var(--faint);margin-top:2px}
#search{width:100%;font:.9rem var(--sans);padding:6px 8px;border:1px solid var(--rule-strong);background:var(--surface);color:var(--ink);border-radius:3px}
#info{background:var(--surface);border:1px solid var(--rule-strong);border-left:2px solid var(--accent);padding:12px 14px;margin-top:6px;min-height:120px}
#info .hint{font-family:var(--serif);font-style:italic;color:var(--muted)}
#info .name{font-family:var(--serif);font-size:1.25rem;font-weight:600;line-height:1.15}
#info .where{color:var(--muted);font-size:.85rem}
#info .facts{font:.78rem var(--mono);color:var(--faint);margin:.3rem 0 .55rem}
.score-big{font-family:var(--serif);font-size:2rem;font-weight:500;line-height:1}
.score-big small{font-size:.85rem;color:var(--faint);font-family:var(--sans)}
table.svc{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:.84rem;margin-top:.5rem}
table.svc th{font-size:.66rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);text-align:right;border-top:1.5px solid var(--ink);border-bottom:1.5px solid var(--ink);padding:3px 4px}
table.svc th:first-child,table.svc td:first-child{text-align:left}
table.svc td{padding:3px 4px;text-align:right;border-bottom:1px solid var(--rule)}
table.svc tr:last-child td{border-bottom:1.5px solid var(--ink)}
.bar{display:inline-block;height:8px;vertical-align:middle;margin-right:5px;border-radius:1px}
.extra{font-size:.8rem;color:var(--muted);margin-top:.5rem}
.lived{margin-top:.6rem;padding:.5rem .6rem;background:var(--accent-tint);font-size:.84rem}
.lived b{font-variant:small-caps;letter-spacing:.04em;color:var(--accent)}
.places button{display:block;width:100%;text-align:left;font:inherit;background:none;border:0;border-bottom:1px solid var(--rule);padding:6px 0;cursor:pointer;color:var(--ink)}
.places button b{font-family:var(--serif);font-weight:600}
.places button span{display:block;font-size:.8rem;color:var(--muted)}
.places button:hover b{color:var(--accent)}
.note{font-size:.76rem;color:var(--faint);margin-top:1rem;padding-top:.6rem;border-top:3px double var(--rule-strong)}
.note a{color:var(--muted)}
.leaflet-container{font-family:var(--sans)}
.basemap{filter:grayscale(1) sepia(.3) contrast(.85) brightness(1.06)}
.lived-label{background:var(--surface);border:1px solid var(--accent);color:var(--ink);font:600 .78rem var(--serif);box-shadow:none;padding:1px 6px}
.lived-label:before{display:none}
@media (max-width:760px){
  #app{grid-template-columns:1fr;grid-template-rows:55vh auto;height:auto}
  #map{height:55vh;order:-1}
  #side{border-right:0;border-top:1px solid var(--rule-strong);padding:16px}
  h1{font-size:1.5rem}
}
</style>
</head>
<body>
<div id="app">
<aside id="side">
  <div class="kicker">Metro Manila &middot; 1,710 barangays</div>
  <h1>Who can <em>walk</em> to the basics?</h1>
  <p class="lead">Every barangay scored 0-100 on walking access to groceries, healthcare, parks, transit and schools.
  A resident counts fully within a 5 minute walk, two-thirds within 10 and a third within 15.</p>

  <h2>Colour the map by</h2>
  <div class="sel" id="sel"></div>
  <div class="legend" id="legend"></div>
  <div class="legend-l" id="legend-l"></div>

  <h2>Barangay</h2>
  <input id="search" list="names" placeholder="Find a barangay, e.g. Oranbo" autocomplete="off">
  <datalist id="names"></datalist>
  <div id="info"><span class="hint">Hover over (or tap) a barangay to see its scores.</span></div>

  <h2>Places I have lived</h2>
  <div class="places" id="places"></div>

  <div class="note">
    Population: PSA 2020 census, placed into Overture buildings with WorldPop 100 m.
    Services: Overture Maps __RELEASE__ (groceries, healthcare, schools, parks) and OpenStreetMap
    (LRT/MRT, bus and jeepney stops and routes, public markets), snapshot __OSM__.
    Distances are along the OpenStreetMap walking network at 4.5 km/h.
    Boundaries: PSA / NAMRIA via HDX.
    <a href="https://github.com/earlcyu-petcircle/metro-manila-accessibility">Method and code</a>.
  </div>
</aside>
<div id="map"></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const BRGY = __BARANGAYS__;
const LIVED = __LIVED__;
const LABELS = __LABELS__;
const BREAKS = __BREAKS__, COLOURS = __COLOURS__;
const SERVICES = ["grocery", "health", "parks", "transit", "schools"];

let field = "composite";
const colour = v => v == null ? "#D9CFBA" : COLOURS[BREAKS.filter(b => v >= b).length];
const val = p => field === "composite" ? p.composite : p["score_" + field];
const fmt = n => n == null ? "-" : Math.round(n).toLocaleString("en-AU");
const metres = m => m == null ? "-" : (m >= 1000 ? (m / 1000).toFixed(1) + " km" : Math.round(m) + " m");
const mins = m => m == null ? "" : Math.round(m / 75) + " min";

const map = L.map("map", {zoomControl: true, preferCanvas: false}).setView([14.6, 121.03], 11);
// Keyless base tiles: OpenStreetMap standard, muted with a CSS filter (CARTO now needs a key).
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, className: "basemap",
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const style = f => ({fillColor: colour(val(f.properties)), fillOpacity: 0.78, color: "#FFFDF7", weight: 0.4});
let selected = null;
const layer = L.geoJSON(BRGY, {
  style,
  onEachFeature: (f, l) => {
    l.on({
      mouseover: () => { highlight(l); show(f.properties); },
      mouseout: () => { if (selected !== l) layer.resetStyle(l); if (selected) show(selected.feature.properties); },
      click: () => { select(l); }
    });
  }
}).addTo(map);
map.fitBounds(layer.getBounds(), {padding: [10, 10]});

L.geoJSON(LIVED, {
  interactive: false,
  style: {color: "#96700F", weight: 2.6, dashArray: "6 4", fill: false},
  onEachFeature: (f, l) => l.bindTooltip(f.properties.label, {permanent: true, direction: "center", className: "lived-label"})
}).addTo(map);

function highlight(l) { l.setStyle({weight: 2.2, color: "#292216"}); l.bringToFront(); }
function select(l) {
  if (selected && selected !== l) layer.resetStyle(selected);
  selected = l; highlight(l); show(l.feature.properties);
}

function show(p) {
  const place = p.district ? `${p.district}, ${p.city}` : p.city;
  if (p.composite == null) {
    document.getElementById("info").innerHTML = `<div class="name">${p.barangay}</div><div class="where">${place}</div>
      <div class="facts">No census population, so no score.</div>`;
    return;
  }
  const rows = SERVICES.map(s => {
    const sc = p["score_" + s];
    return `<tr><td><span class="bar" style="width:${Math.max(2, sc * 0.45)}px;background:${colour(sc)}"></span>${LABELS[s]}</td>
      <td>${fmt(sc)}</td><td>${fmt(p[s + "_share5"])}%</td><td>${metres(p[s + "_median_m"])}</td></tr>`;
  }).join("");
  const lived = p.place_lived ? LIVED.features.find(f => f.properties.place_lived === p.place_lived).properties : null;
  document.getElementById("info").innerHTML = `
    <div class="name">${p.barangay}</div>
    <div class="where">${place}</div>
    <div class="facts">${fmt(p.pop2020)} people (2020) &middot; ${fmt(p.density_km2)} per km&sup2;</div>
    <div class="score-big">${p.composite.toFixed(0)}<small> / 100 &nbsp;all services</small></div>
    <table class="svc"><thead><tr><th>Service</th><th>Score</th><th>&le;5 min</th><th>Typical walk</th></tr></thead>
    <tbody>${rows}</tbody></table>
    <div class="extra">Public market (palengke): ${fmt(p.palengke_share5)}% within 5 min, typical walk ${metres(p.palengke_median_m)} (${mins(p.palengke_median_m)}).<br>
    LRT/MRT stop: typical walk ${metres(p.rail_median_m)} (${mins(p.rail_median_m)}).</div>
    ${lived ? `<div class="lived"><b>Places I have lived &middot; ${lived.label}</b><br>${lived.note}</div>` : ""}
    <div class="extra" style="font-size:.72rem;color:#8B8069">&ldquo;Typical walk&rdquo; is the median resident's walk to the nearest one.</div>`;
}

// Selector and legend
const sel = document.getElementById("sel");
Object.entries(LABELS).forEach(([k, label]) => {
  const b = document.createElement("button");
  b.textContent = label; b.setAttribute("aria-pressed", k === field);
  b.onclick = () => {
    field = k; layer.setStyle(style);
    if (selected) highlight(selected);
    sel.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
  };
  sel.appendChild(b);
});
document.getElementById("legend").innerHTML = COLOURS.map(c => `<span style="background:${c}"></span>`).join("");
document.getElementById("legend-l").innerHTML = ["0", ...BREAKS, "100"].map(x => `<span>${x}</span>`).join("");

// Search
const byName = {};
BRGY.features.forEach(f => { byName[`${f.properties.barangay}, ${f.properties.district || f.properties.city}`] = f; });
document.getElementById("names").innerHTML = Object.keys(byName).sort().map(n => `<option value="${n}">`).join("");
document.getElementById("search").addEventListener("change", e => {
  const f = byName[e.target.value];
  if (!f) return;
  layer.eachLayer(l => { if (l.feature === f) { map.fitBounds(l.getBounds(), {maxZoom: 15}); select(l); } });
});

// Places lived
const places = document.getElementById("places");
LIVED.features.forEach(f => {
  const p = f.properties, b = document.createElement("button");
  b.innerHTML = `<b>${p.label}</b><span>${p.years} &middot; ${p.note}</span>`;
  b.onclick = () => map.fitBounds(L.geoJSON(f).getBounds(), {maxZoom: 15, padding: [20, 20]});
  places.appendChild(b);
});
</script>
</body>
</html>
"""

subs = {
    "__BG__": BG, "__SURFACE__": SURFACE, "__INK__": INK, "__MUTED__": MUTED, "__FAINT__": FAINT,
    "__RULE__": RULE, "__ACCENT__": ACCENT,
    "__RELEASE__": OVERTURE_RELEASE, "__OSM__": headline["osm_snapshot"][:10],
    "__BARANGAYS__": json.dumps(barangays, separators=(",", ":"), ensure_ascii=False),
    "__LIVED__": json.dumps(lived, separators=(",", ":"), ensure_ascii=False),
    "__LABELS__": json.dumps(SERVICE_LABELS), "__BREAKS__": json.dumps(SCORE_BREAKS),
    "__COLOURS__": json.dumps(SCORE_COLOURS),
}
for k, v in subs.items():
    page = page.replace(k, v)
(DOCS / "index.html").write_text(page)
print(f"wrote docs/index.html  ({len(page) / 1e6:.1f} MB)")
