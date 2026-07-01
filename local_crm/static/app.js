const state = { page: "dashboard", farmacias: [], dashboard: null, selectedFarmacia: null };
const stages = ["Sin contactar", "Contactada", "Reunion", "Propuesta", "Cliente"];

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, s => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[s]));
}

async function loadData() {
  state.dashboard = await api("/api/dashboard");
  state.farmacias = await api("/api/farmacias");
}

function setHeader(title, sub) {
  document.getElementById("page-title").textContent = title;
  document.getElementById("page-sub").textContent = sub || "";
}

function kpi(label, value) {
  return `<div class="kpi-card"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div></div>`;
}

function renderDashboard() {
  const d = state.dashboard;
  const stageCounts = [0, 1, 2, 3, 4].map(i => {
    const row = d.stages.find(s => Number(s.etapa) === i);
    return row ? Number(row.total) : 0;
  });
  const max = Math.max(...stageCounts, 1);
  setHeader("Dashboard", "Estado comercial en tiempo real desde SQLite");
  return `
    <div class="kpi-grid">
      ${kpi("Farmacias", d.total)}
      ${kpi("Clientes activos", d.clientes)}
      ${kpi("Reuniones", d.reuniones)}
      ${kpi("Expedientes", d.expedientes)}
    </div>
    <div class="panel">
      <div class="panel-header"><div class="panel-title">Embudo de ventas</div></div>
      <div class="panel-body">
        <div class="funnel">
          ${stages.map((stage, i) => `
            <div class="funnel-stage">
              <div class="funnel-bar" style="height:${Math.max(26, Math.round(stageCounts[i] / max * 120))}px">${stageCounts[i]}</div>
              <div class="funnel-label">${stage}</div>
            </div>
          `).join("")}
        </div>
      </div>
    </div>
    ${renderFarmaciasTable(state.farmacias.slice(0, 12), "Ultimas farmacias cargadas")}
  `;
}

function renderFarmaciasTable(rows, title = "Farmacias") {
  return `
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">${title}</div>
        <div class="toolbar">
          <input id="search" placeholder="Buscar farmacia, municipio..." />
        </div>
      </div>
      <table>
        <thead><tr><th>Nombre</th><th>Provincia</th><th>Municipio</th><th>Telefono</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          ${rows.map(row => `
            <tr>
              <td>${esc(row.nombre_comercial)}</td>
              <td>${esc(row.provincia)}</td>
              <td>${esc(row.municipio)}</td>
              <td>${esc(row.telefono)}</td>
              <td><span class="badge ${row.estado_contacto === "Activa" ? "badge-active" : "badge-pot"}">${esc(row.estado_contacto)}</span></td>
              <td><button class="btn btn-ghost" data-view="${row.id}">Ver</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderFarmacias() {
  setHeader("Farmacias", `${state.farmacias.length} registros importados desde Excel`);
  return renderFarmaciasTable(state.farmacias, "Base de datos");
}

async function renderFarmaciaDetail(id) {
  const data = await api(`/api/farmacias/${id}`);
  const f = data.farmacia;
  setHeader(f.nombre_comercial, `${f.provincia || ""} · ${f.municipio || ""}`);
  document.getElementById("view").innerHTML = `
    <div class="grid-2">
      <div class="panel">
        <div class="panel-header"><div class="panel-title">Ficha</div></div>
        <div class="panel-body detail">
          ${["telefono","calle","numero","codigo_postal","localidad","municipio","provincia","estado_contacto"].map(k => `
            <div class="detail-item"><div class="detail-label">${k}</div><div class="detail-value">${esc(f[k])}</div></div>
          `).join("")}
        </div>
      </div>
      <div class="panel">
        <div class="panel-header"><div class="panel-title">Crear expediente</div></div>
        <div class="panel-body">
          <form id="exp-form">
            <input type="hidden" name="farmacia_id" value="${f.id}" />
            <p><input name="titulo" placeholder="Titulo del expediente" required /></p>
            <p><select name="tipo"><option>Auditoria</option><option>Asesoria</option></select></p>
            <p><textarea name="descripcion" placeholder="Descripcion"></textarea></p>
            <button class="btn btn-primary">Crear expediente</button>
          </form>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-header"><div class="panel-title">Expedientes</div></div>
      <table>
        <thead><tr><th>Titulo</th><th>Tipo</th><th>Estado</th><th>Ruta local</th><th></th></tr></thead>
        <tbody>${data.expedientes.map(e => `
          <tr><td>${esc(e.titulo)}</td><td>${esc(e.tipo)}</td><td>${esc(e.estado)}</td><td>${esc(e.carpeta_path)}</td><td><button class="btn btn-gold" data-audit="${e.id}">Generar auditoria</button></td></tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
  document.getElementById("exp-form").onsubmit = async ev => {
    ev.preventDefault();
    await api("/api/expedientes", { method: "POST", body: new FormData(ev.target) });
    await renderFarmaciaDetail(id);
  };
  document.querySelectorAll("[data-audit]").forEach(btn => {
    btn.onclick = async () => {
      const result = await api(`/api/expedientes/${btn.dataset.audit}/generar-auditoria`, { method: "POST" });
      alert(result.resumen || "Analisis solicitado");
    };
  });
}

function render() {
  const view = document.getElementById("view");
  if (state.page === "dashboard") view.innerHTML = renderDashboard();
  if (state.page === "farmacias" || state.page === "pipeline" || state.page === "clientes") view.innerHTML = renderFarmacias();
  if (state.page === "expedientes") {
    setHeader("Expedientes", "Selecciona una farmacia para gestionar sus expedientes");
    view.innerHTML = renderFarmaciasTable(state.farmacias, "Seleccionar farmacia");
  }
  attachEvents();
}

function attachEvents() {
  document.querySelectorAll(".nav-item").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".nav-item").forEach(x => x.classList.remove("active"));
      btn.classList.add("active");
      state.page = btn.dataset.page;
      render();
    };
  });
  document.querySelectorAll("[data-view]").forEach(btn => btn.onclick = () => renderFarmaciaDetail(btn.dataset.view));
  const search = document.getElementById("search");
  if (search) search.oninput = () => {
    const q = search.value.toLowerCase();
    const rows = state.farmacias.filter(f => [f.nombre_comercial, f.municipio, f.provincia].join(" ").toLowerCase().includes(q));
    document.getElementById("view").innerHTML = renderFarmaciasTable(rows, "Base de datos");
    attachEvents();
  };
}

document.getElementById("refresh-btn").onclick = async () => { await loadData(); render(); };
loadData().then(render).catch(err => {
  document.getElementById("view").innerHTML = `<div class="panel"><div class="panel-body">Error cargando CRM: ${esc(err.message)}</div></div>`;
});
