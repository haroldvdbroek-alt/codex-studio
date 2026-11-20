"use strict";

function hasUpdate(project) {
  return ["NIEUW_BESCHIKBAAR", "GROTE_WIJZIGING"].includes(project.update);
}
function needsAttention(project) {
  return project.configuration !== "PASS" || project.git !== "PASS" || project.update !== "ACTUEEL";
}
function summary(items) {
  return {total: items.length, attention: items.filter(needsAttention).length, updates: items.filter(hasUpdate).length};
}
function filterProjects(items, query, type, status) {
  const name = query.trim().toLocaleLowerCase("nl-NL");
  return items.filter(project => String(project.name).toLocaleLowerCase("nl-NL").includes(name) &&
    (!type || project.type === type) && (!status ||
      (status === "attention" && needsAttention(project)) ||
      (status === "updates" && hasUpdate(project)) ||
      (status === "ready" && !needsAttention(project))));
}

function initDashboard(document, request = fetch) {
  const byId = id => document.getElementById(id);
  const state = byId("state"), projects = byId("projects"), warnings = byId("warnings");
  const refresh = byId("refresh"), details = byId("details"), empty = byId("empty");
  const search = byId("search"), type = byId("type-filter"), status = byId("status-filter");
  let loading = false, items = [], available = false;
  let scanState = "BEZIG";
  let detailButton = null;

  function closeDetails(returnFocus = false) {
    details.hidden = true;
    byId("detail-fields").replaceChildren();
    byId("details-title").textContent = "Projectdetails";
    if (detailButton) {
      detailButton.setAttribute("aria-expanded", "false");
      if (returnFocus) detailButton.focus();
    }
    detailButton = null;
  }
  function openDetails(project, button) {
    closeDetails();
    detailButton = button;
    button.setAttribute("aria-expanded", "true");
    byId("details-title").textContent = String(project.name);
    for (const [label, value] of [["Projecttype", project.type], ["Templateversie", project.template_version ?? "onbekend"],
      ["Lokale templateversie", project.local_version ?? "onbekend"], ["Update", project.update],
      ["Configuratie", project.configuration], ["Git", project.git], ["Tests", "NIET_UITGEVOERD"]]) {
      const term = document.createElement("dt"), description = document.createElement("dd");
      term.textContent = label;
      description.textContent = String(value ?? "onbekend");
      byId("detail-fields").appendChild(term);
      byId("detail-fields").appendChild(description);
    }
    details.hidden = false;
    details.focus();
  }
  function textCell(value) {
    const cell = document.createElement("td");
    cell.textContent = String(value);
    if (["PASS", "ACTUEEL"].includes(value)) cell.className = "status-good";
    if (["WARN", "NIEUW_BESCHIKBAAR", "PROJECT_LOOPT_VOOR"].includes(value)) cell.className = "status-warn";
    if (["FAIL", "GROTE_WIJZIGING"].includes(value)) cell.className = "status-fail";
    return cell;
  }
  function render() {
    closeDetails();
    projects.replaceChildren();
    const visible = filterProjects(items, search.value, type.value, status.value);
    for (const project of visible) {
      const row = document.createElement("tr");
      for (const value of [project.name, project.type, project.template_version ?? "onbekend", project.local_version ?? "onbekend",
        project.update, project.configuration, project.git, "NIET_UITGEVOERD"]) row.appendChild(textCell(value));
      const cell = document.createElement("td"), button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = "Bekijken";
      button.setAttribute("aria-controls", "details");
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", "Details bekijken van " + String(project.name));
      button.addEventListener("click", () => openDetails(project, button));
      cell.appendChild(button);
      row.appendChild(cell);
      projects.appendChild(row);
    }
    const counts = summary(items);
    for (const key of ["total", "attention", "updates"]) byId(key).textContent = available ? String(counts[key]) : "—";
    byId("result-count").textContent = available ? `${visible.length} van ${items.length} project(en) zichtbaar` : "";
    empty.hidden = !available || visible.length !== 0;
    empty.textContent = items.length ? "Geen projecten met deze filters. Wis de filters om alle projecten te bekijken." :
      scanState === "BEZIG" ? "De eerste scan loopt nog. Wacht op het volgende overzicht." :
      scanState === "ONVOLLEDIG" ? "Geen projecten in dit onvolledige overzicht. Controleer de meldingen hierboven." :
      "Geen geregistreerde projecten gevonden. Controleer de gekozen projectroot en eventuele meldingen hierboven; projecten hebben .codex-studio.json nodig.";
  }
  async function loadProjects() {
    if (loading) return;
    loading = true;
    refresh.disabled = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await request("/api/projects", {
        method: "GET", cache: "no-store", credentials: "omit", redirect: "error", signal: controller.signal
      });
      if (!response.ok) throw new Error("Geen resultaat");
      const data = await response.json();
      if (!data || !Array.isArray(data.projects) || data.projects.length > 100 ||
          !data.projects.every(project => project && typeof project === "object" && typeof project.name === "string") ||
          !Array.isArray(data.warnings) || data.warnings.length > 500 ||
          !data.warnings.every(warning => typeof warning === "string")) throw new Error("Ongeldig resultaat");
      const changed = !available || scanState !== data.state || JSON.stringify(items) !== JSON.stringify(data.projects);
      scanState = data.state;
      items = data.projects;
      available = true;
      warnings.replaceChildren();
      for (const warning of data.warnings) {
        const item = document.createElement("li");
        item.textContent = warning;
        warnings.appendChild(item);
      }
      if (changed) render();
      state.textContent = `${items.length} project(en) · ${String(data.state)} · opgehaald om ${new Date().toLocaleTimeString("nl-NL")}`;
    } catch {
      items = [];
      available = false;
      warnings.replaceChildren();
      render();
      state.textContent = "Overzicht niet beschikbaar. Controleer of de lokale server nog draait en probeer opnieuw. Eerdere resultaten zijn niet meer actueel.";
    } finally {
      clearTimeout(timeout);
      loading = false;
      refresh.disabled = false;
    }
  }
  search.addEventListener("input", render);
  type.addEventListener("change", render);
  status.addEventListener("change", render);
  byId("reset-filters").addEventListener("click", () => {
    search.value = ""; type.value = ""; status.value = ""; render(); search.focus();
  });
  byId("close-details").addEventListener("click", () => closeDetails(true));
  details.addEventListener("keydown", event => { if (event.key === "Escape") closeDetails(true); });
  refresh.addEventListener("click", loadProjects);
  const ready = loadProjects();
  setInterval(loadProjects, 5000);
  return {ready, loadProjects};
}

if (typeof module !== "undefined" && module.exports) module.exports = {summary, filterProjects, needsAttention, initDashboard};
if (typeof document !== "undefined") initDashboard(document);
