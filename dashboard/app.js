"use strict";

const state = document.getElementById("state");
const projects = document.getElementById("projects");
const warnings = document.getElementById("warnings");
const refresh = document.getElementById("refresh");
let loading = false;

async function loadProjects() {
  if (loading) return;
  loading = true;
  refresh.disabled = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch("/api/projects", {
      cache: "no-store", credentials: "omit", redirect: "error", signal: controller.signal
    });
    if (!response.ok) throw new Error("Geen resultaat");
    const data = await response.json();
    projects.replaceChildren();
    warnings.replaceChildren();
    for (const project of data.projects) {
      const row = document.createElement("tr");
      for (const value of [project.name, project.type, project.template_version ?? "onbekend",
        project.local_version, project.update, project.configuration, project.git, "NIET_UITGEVOERD"]) {
        const cell = document.createElement("td");
        cell.textContent = String(value);
        row.appendChild(cell);
      }
      projects.appendChild(row);
    }
    for (const warning of data.warnings) {
      const item = document.createElement("li");
      item.textContent = warning;
      warnings.appendChild(item);
    }
    document.getElementById("empty").hidden = data.projects.length !== 0;
    state.textContent = `${data.projects.length} project(en) · ${data.state} · opgehaald om ${new Date().toLocaleTimeString("nl-NL")}`;
  } catch {
    projects.replaceChildren();
    warnings.replaceChildren();
    state.textContent = "Overzicht niet beschikbaar. Controleer of de lokale server nog draait.";
  } finally {
    clearTimeout(timeout);
    loading = false;
    refresh.disabled = false;
  }
}

refresh.addEventListener("click", loadProjects);
loadProjects();
setInterval(loadProjects, 5000);
