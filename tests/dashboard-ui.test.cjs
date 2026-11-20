"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {summary, filterProjects, needsAttention, initDashboard} = require("../dashboard/app.js");

// Geen browser, netwerk, echte projecten of achtergrondtimers nodig.
global.setInterval = () => 0;
class Element {
  constructor() { this.children = []; this.events = {}; this.attributes = {}; this.value = ""; this.hidden = false; this.text = ""; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(""); }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.text = ""; this.children = children; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(key, callback) { this.events[key] = callback; }
  emit(key, event = {}) { return this.events[key](event); }
  focus() { this.focused = true; }
}
function fixture() {
  const elements = new Map();
  const document = {getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    createElement() { return new Element(); }};
  document.getElementById("details").hidden = true;
  return {document, get: id => document.getElementById(id)};
}
const project = (name, extra = {}) => ({name, type: "python", template_version: "1.0.0", local_version: "1.0.0",
  configuration: "PASS", git: "PASS", update: "ACTUEEL", ...extra});
const payload = projects => ({projects, warnings: [], state: "GEREED"});

test("samenvatting onderscheidt aandacht, updates en niet-beoordeelde tests", () => {
  const items = [project("Goed"), project("Gewijzigd", {git: "WARN"}), project("Update", {update: "NIEUW_BESCHIKBAAR"}),
    project("Groot", {update: "GROTE_WIJZIGING"}), project("Voor", {update: "PROJECT_LOOPT_VOOR"}), project("Onbekend", {update: "ONBEKEND"})];
  assert.deepEqual(summary(items), {total: 6, attention: 5, updates: 2});
  assert.equal(needsAttention(project("Geen testbewijs", {tests: "NIET_UITGEVOERD"})), false);
});
test("zoeken, type en status combineren zonder gegevens te wijzigen", () => {
  const items = [project("Mijn Notities"), project("Mijn web", {type: "web", git: "WARN"}), project("Ander")];
  const before = JSON.stringify(items);
  assert.deepEqual(filterProjects(items, " MIJN ", "web", "attention").map(p => p.name), ["Mijn web"]);
  assert.equal(filterProjects(items, "", "", "ready").length, 2);
  assert.equal(filterProjects(items, "", "", "updates").length, 0);
  assert.equal(JSON.stringify(items), before);
});
test("projectnaam en waarschuwing blijven letterlijke tekst; details starten geen verzoek", async () => {
  const {document, get} = fixture(), calls = [];
  const attack = '<img src=x onerror="alert(1)">';
  const app = initDashboard(document, async (...args) => { calls.push(args); return {ok: true,
    json: async () => ({projects: [project(attack, {tests: "PASS"})], warnings: [attack], state: "GEREED"})}; });
  await app.ready;
  assert.equal(get("projects").children[0].children[0].textContent, attack);
  assert.equal(get("warnings").children[0].textContent, attack);
  assert.equal(get("projects").children[0].children[7].textContent, "NIET_UITGEVOERD");
  const button = get("projects").children[0].children[8].children[0];
  button.emit("click");
  assert.equal(get("details").hidden, false);
  assert.equal(get("details").focused, true);
  assert.equal(get("details-title").textContent, attack);
  assert.ok(get("detail-fields").textContent.includes("NIET_UITGEVOERD"));
  get("details").emit("keydown", {key: "Escape"});
  assert.equal(get("details").hidden, true);
  assert.equal(button.focused, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "/api/projects");
  assert.equal(calls[0][1].method, "GET");
  assert.equal(calls[0][1].credentials, "omit");
});
test("filters en details blijven behouden bij een ongewijzigde snapshot", async () => {
  const {document, get} = fixture();
  const app = initDashboard(document, async () => ({ok: true, json: async () => payload([project("Een"), project("Twee")])}));
  await app.ready;
  get("search").value = "Een";
  get("search").emit("input");
  get("projects").children[0].children[8].children[0].emit("click");
  await app.loadProjects();
  assert.equal(get("projects").children.length, 1);
  assert.equal(get("details").hidden, false);
  get("search").value = "Geen match";
  get("search").emit("input");
  assert.equal(get("empty").hidden, false);
  assert.ok(get("empty").textContent.includes("filters"));
  get("reset-filters").emit("click");
  assert.equal(get("projects").children.length, 2);
  assert.equal(get("search").focused, true);
});
test("lege snapshot legt registratie uit", async () => {
  const {document, get} = fixture();
  await initDashboard(document, async () => ({ok: true, json: async () => payload([])})).ready;
  assert.equal(get("empty").hidden, false);
  assert.ok(get("empty").textContent.includes(".codex-studio.json"));
});
test("lopende en onvolledige scans worden niet als afwezige projecten gepresenteerd", async () => {
  const {document, get} = fixture();
  let state = "BEZIG";
  const app = initDashboard(document, async () => ({ok: true, json: async () => ({projects: [], warnings: [], state})}));
  await app.ready;
  assert.ok(get("empty").textContent.includes("scan loopt"));
  state = "ONVOLLEDIG";
  await app.loadProjects();
  assert.ok(get("empty").textContent.includes("onvolledige"));
});
test("HTTP- en JSON-fouten verwijderen eerdere data en tonen geen ruwe exception", async () => {
  for (const bad of [null, {projects: null, warnings: []}, {projects: Array(101).fill(project("groot")), warnings: []},
    {projects: [], warnings: [null]}, {projects: [null], warnings: []}]) {
    const {document, get} = fixture();
    let fail = false;
    const app = initDashboard(document, async () => ({ok: true, json: async () => fail ? bad : payload([project("Oud")])}));
    await app.ready;
    get("projects").children[0].children[8].children[0].emit("click");
    fail = true;
    await app.loadProjects();
    assert.equal(get("projects").children.length, 0);
    assert.equal(get("details").hidden, true);
    assert.equal(get("total").textContent, "—");
    assert.equal(get("refresh").disabled, false);
  }
  const {document, get} = fixture();
  await initDashboard(document, async () => { throw new Error("FICTIEF_GEHEIM"); }).ready;
  assert.ok(get("state").textContent.includes("niet beschikbaar"));
  assert.ok(!get("state").textContent.includes("FICTIEF_GEHEIM"));
});
