(() => {
  const $ = (selector) => document.querySelector(selector);
  const main = document.querySelector("main");
  const nav = document.querySelector("#nav");
  if (!main || !nav || document.querySelector("#estadisticas")) return;

  const link = document.createElement("a");
  link.href = "#estadisticas";
  link.textContent = "Estadísticas";
  nav.insertBefore(link, nav.querySelector("a[href='#cuenta']") || null);

  const section = document.createElement("section");
  section.id = "estadisticas";
  section.className = "section stats-dashboard";
  section.innerHTML = `
    <p class="eyebrow">VANTARMOR EN NÚMEROS</p>
    <h2>Estadísticas y estado</h2>
    <p class="stats-intro">Datos actuales del bot y de la comunidad.</p>
    <div class="metric-circles">
      <article class="metric-circle-card"><div class="metric-circle" id="metric-bot"><span id="metric-bot-icon">🔴</span></div><strong id="metric-bot-label">Desconocido</strong><small>Estado del bot</small></article>
      <article class="metric-circle-card"><div class="metric-circle"><strong id="metric-servers">—</strong></div><strong>Servidores</strong><small>Donde está el bot</small></article>
      <article class="metric-circle-card"><div class="metric-circle"><strong id="metric-users">—</strong></div><strong>Usuarios web</strong><small>Han iniciado sesión</small></article>
      <article class="metric-circle-card"><div class="metric-circle"><strong id="metric-commands">—</strong></div><strong>Comandos slash</strong><small>Registrados en el bot</small></article>
    </div>
    <div class="security-stat-panel"><p class="eyebrow">SEGURIDAD INCLUIDA</p><h3>Protecciones de Vantarmor</h3><ul id="security-feature-list"><li>Cargando funciones…</li></ul></div>
    <p id="stats-updated" class="stats-updated" aria-live="polite"></p>`;
  main.append(section);

  link.addEventListener("click", (event) => {
    event.preventDefault();
    if (typeof window.activateTab === "function") window.activateTab("estadisticas");
  });

  async function refresh() {
    const status = $("#stats-updated");
    try {
      const response = await fetch("/api/stats", { credentials: "same-origin", cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "No se pudieron cargar las estadísticas.");
      const online = Boolean(data.bot_online);
      $("#metric-bot-icon").textContent = online ? "🟢" : "🔴";
      $("#metric-bot-label").textContent = online ? "Encendido" : "Apagado";
      $("#metric-bot").classList.toggle("is-online", online);
      $("#metric-servers").textContent = Number(data.servers || 0).toLocaleString("es");
      $("#metric-users").textContent = Number(data.website_users || 0).toLocaleString("es");
      $("#metric-commands").textContent = Number(data.slash_commands || 0).toLocaleString("es");
      const list = $("#security-feature-list");
      list.replaceChildren(...(data.security_features || []).map((feature) => {
        const item = document.createElement("li");
        item.textContent = `🛡️ ${feature}`;
        return item;
      }));
      status.textContent = `Actualizado: ${new Date().toLocaleTimeString("es")}`;
    } catch (error) {
      status.textContent = error.message || "No se pudieron cargar las estadísticas.";
    }
  }
  refresh();
  window.setInterval(refresh, 30000);
})();
