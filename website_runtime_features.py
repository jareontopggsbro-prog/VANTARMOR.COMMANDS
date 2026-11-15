"""Install website guild filtering, statistics assets, and live Discord status hooks."""
import os
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

import guild_profile_settings

_STATUS_LOCK = threading.RLock()
_STATUS = {"online": False, "servers": 0, "slash_commands": 0}
_STATS_FEATURES = [
    "Anti-Raid y alertas de seguridad",
    "Anti-Nuke con modo pánico manual",
    "Anti-Bot y lista autorizada",
    "Filtro de cuentas nuevas",
    "Moderación y bloqueo de canales",
    "Tickets, registros y copias de seguridad",
]


def set_bot_status(online, guild_count=0, command_count=0):
    with _STATUS_LOCK:
        _STATUS.update(
            online=bool(online),
            servers=max(0, int(guild_count)),
            slash_commands=max(0, int(command_count)),
        )


def _bot_present_guilds(guilds):
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError("El bot no está configurado en este servicio.")
    present = []
    for guild in guilds:
        guild_id = str(guild.get("id", ""))
        if not guild_id.isdecimal():
            continue
        try:
            guild_profile_settings._discord_json(f"/guilds/{guild_id}", token=token)
        except HTTPError as error:
            if error.code in (403, 404):
                continue
            raise
        present.append(guild)
    return present


def install_website_api(handler_class):
    """Filter selectable guilds to bot-installed servers and serve live stats."""
    previous_get = handler_class.do_GET

    def do_get(self):
        path = urlparse(self.path).path
        if path == "/api/guilds":
            session = self.get_session()
            if not session:
                return self.send_json({"error": "inicia_sesion"}, 401)
            try:
                user_guilds = self.server.discord_request("/users/@me/guilds", token=session["access_token"])
                manageable = [
                    guild for guild in user_guilds
                    if guild.get("owner") or int(guild.get("permissions", "0")) & (0x8 | 0x20)
                ]
                present = _bot_present_guilds(manageable)
                return self.send_json({"guilds": [{"id": guild["id"], "name": guild["name"]} for guild in present]})
            except (HTTPError, URLError, OSError, ValueError, TypeError):
                return self.send_error_json("No se pudieron cargar servidores donde el bot esté instalado.", 502)

        if path == "/api/stats":
            from premium_store import public_stats

            stats = public_stats()
            with _STATUS_LOCK:
                status = dict(_STATUS)
            stats.update(
                bot_online=status["online"],
                servers=status["servers"],
                slash_commands=status["slash_commands"],
                security_features=_STATS_FEATURES,
            )
            return self.send_json(stats)
        return previous_get(self)

    handler_class.do_GET = do_get


def install_bot_status_hooks(app_file):
    """Patch app.py so website status reflects Discord gateway readiness."""
    source = app_file.read_text(encoding="utf-8")
    marker = "# VANTARMOR_WEBSITE_STATUS_HOOKS_V1"
    if marker in source:
        return

    import_anchor = "from discord import app_commands\n"
    if "import website_runtime_features\n" not in source:
        if import_anchor not in source:
            raise RuntimeError("No encontré el bloque de imports de app.py para el estado web.")
        source = source.replace(import_anchor, import_anchor + "import website_runtime_features\n", 1)

    ready_anchor = '    print(f"Conectado como {client.user}")\n'
    ready_status = "    website_runtime_features.set_bot_status(True, len(client.guilds), len(tree.get_commands()))\n"
    if ready_anchor not in source:
        raise RuntimeError("No encontré on_ready para actualizar el estado de la web.")
    if ready_status not in source:
        source = source.replace(ready_anchor, ready_anchor + ready_status, 1)

    run_anchor = "client.run(TOKEN)\n"
    if run_anchor not in source:
        raise RuntimeError("No encontré client.run para conectar el estado web.")
    disconnect_hooks = (
        "@client.event\n"
        "async def on_disconnect():\n"
        "    website_runtime_features.set_bot_status(False, len(client.guilds), len(tree.get_commands()))\n\n\n"
        "@client.event\n"
        "async def on_resumed():\n"
        "    website_runtime_features.set_bot_status(True, len(client.guilds), len(tree.get_commands()))\n\n\n"
        f"{marker}\n"
    )
    if marker not in source:
        source = source.replace(run_anchor, disconnect_hooks + run_anchor, 1)
    app_file.write_text(source, encoding="utf-8")


def install_website_assets():
    """Include statistics assets in the existing homepage without replacing it."""
    index_file = os.path.join(os.path.dirname(__file__), "website", "index.html")
    try:
        with open(index_file, encoding="utf-8") as file:
            html = file.read()
    except OSError:
        return
    css = '<link rel="stylesheet" href="/assets/stats.css">'
    script = '<script src="/assets/stats.js" defer></script>'
    if css not in html:
        html = html.replace("</head>", f"  {css}\n</head>", 1)
    if script not in html:
        html = html.replace("</body>", f"  {script}\n</body>", 1)
    with open(index_file, "w", encoding="utf-8") as file:
        file.write(html)


def install_dynamic_tab_support(app_js):
    """Allow the runtime-added stats section to participate in tab navigation."""
    source = app_js.read_text(encoding="utf-8")
    source = source.replace(
        'const tabSections = [...document.querySelectorAll("main > section[id]")];',
        'const getTabSections = () => [...document.querySelectorAll("main > section[id]")];',
    )
    source = source.replace(
        '  const active = tabSections.find((section) => section.id === id) || tabSections[0];',
        '  const tabSections = getTabSections();\n  const active = tabSections.find((section) => section.id === id) || tabSections[0];',
    )
    if "window.activateTab = activateTab;" not in source:
        source = source.replace("function toast(message) {", "window.activateTab = activateTab;\n\nfunction toast(message) {", 1)

    # The account selector must consume the filtered server list, not the raw
    # OAuth list. The API only returns guilds both managed by the user and with
    # the bot installed; the POST endpoint independently verifies this again.
    source = source.replace(
        'const result = await api("/api/settings/guilds");',
        'const result = await api("/api/guilds");',
    )
    selector_anchor = '  const status = $("#guild-profile-message");\n'
    selector_note = '''  const scopeNote = document.createElement("p");
  scopeNote.id = "guild-profile-scope-note";
  scopeNote.textContent = "Selecciona un servidor donde Vantarmor esté instalado. El apodo y el avatar se aplicarán únicamente al perfil del bot en ese servidor.";
  if (!$("#guild-profile-scope-note")) select.insertAdjacentElement("beforebegin", scopeNote);
'''
    if "guild-profile-scope-note" not in source and selector_anchor in source:
        source = source.replace(selector_anchor, selector_anchor + selector_note, 1)

    guilds_anchor = '  const guilds = result.data.guilds || [];\n'
    guilds_guidance = '''  if (select.options.length) select.options[0].textContent = "Elige el servidor donde aplicar los cambios";
  status.textContent = result.data.guilds?.length
    ? "Solo aparecen servidores que administras y donde el bot está unido."
    : "No se encontraron servidores administrables donde el bot esté unido.";
  select.addEventListener("change", () => {
    status.textContent = select.value
      ? `Los próximos cambios se aplicarán únicamente en ${select.selectedOptions[0].text}.`
      : "Selecciona un servidor donde Vantarmor esté instalado.";
  });
'''
    if "Solo aparecen servidores que administras" not in source and guilds_anchor in source:
        source = source.replace(guilds_anchor, guilds_anchor + guilds_guidance, 1)

    app_js.write_text(source, encoding="utf-8")


__all__ = [
    "install_bot_status_hooks",
    "install_dynamic_tab_support",
    "install_website_api",
    "install_website_assets",
    "set_bot_status",
]
