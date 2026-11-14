from pathlib import Path

MARKER = "# VANTARMOR_REACTION_COMMANDS_PATCH_V1"

HELPERS = r'''# VANTARMOR_REACTION_COMMANDS_PATCH_V1
class KillRoleplayView(discord.ui.View):
    """Fictional, non-graphic anime roleplay interaction."""
    def __init__(self, recipient):
        super().__init__(timeout=300)
        self.recipient = recipient

    async def interaction_check(self, interaction):
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("Solo la persona mencionada puede pulsar este botón.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="💚 Volver al combate (roleplay)", style=discord.ButtonStyle.success)
    async def revive(self, interaction, button):
        button.disabled = True
        embed = discord.Embed(
            description=f"💚 {self.recipient.mention} vuelve al combate. ¡Era solo roleplay!",
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=self, allowed_mentions=discord.AllowedMentions.none())


class SpankReturnView(discord.ui.View):
    """Playful, non-sexual anime-style pat interaction."""
    def __init__(self, initiator, recipient):
        super().__init__(timeout=300)
        self.initiator = initiator
        self.recipient = recipient

    async def interaction_check(self, interaction):
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("Este botón es para la persona mencionada.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="😄 Devolver la palmadita", style=discord.ButtonStyle.secondary)
    async def return_pat(self, interaction, button):
        button.disabled = True
        embed = discord.Embed(
            description=f"😄 {self.recipient.mention} le devuelve la palmadita a {self.initiator.mention}.",
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=self, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
'''

KILL_HANDLER = r'''    if command == "?kill":
        target = message.mentions[0] if message.mentions else None
        if target is None and message.reference and message.reference.message_id:
            try:
                referenced = message.reference.resolved
                if referenced is None or not hasattr(referenced, "author"):
                    referenced = await message.channel.fetch_message(message.reference.message_id)
                target = getattr(referenced, "author", None)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                target = None
        if target is None:
            await message.reply("Menciona a alguien o responde a su mensaje con `?kill` (roleplay ficticio).", mention_author=False)
            return True
        if target.bot or target.id == message.author.id:
            await message.reply("Elige a otra persona; este comando es solo roleplay.", mention_author=False)
            return True
        embed = discord.Embed(
            description=f"⚔️ {message.author.mention} derrota a {target.mention} en una pelea de anime y lo deja fuera de combate por un momento. *(Roleplay ficticio, sin daño real.)*",
            color=discord.Color.blurple(),
        )
        image = await random_anime_gif("kill")
        if image:
            embed.set_image(url=image)
        await message.reply(
            embed=embed,
            view=KillRoleplayView(target),
            mention_author=False,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
        return True

'''


def patch_app_file(app_file: Path) -> None:
    source = app_file.read_text(encoding="utf-8")
    handler = "async def handle_reaction_command(message, content):\n"
    if handler not in source:
        raise RuntimeError("No encontré el manejador de comandos de reacción en app.py.")

    # Replace our generated block on each run so deployment is idempotent and
    # cannot retain stale command implementations.
    if MARKER in source:
        start = source.index(MARKER)
        end = source.index(handler, start)
        source = source[:start] + source[end:]
    source = source.replace(handler, HELPERS + "\n\n" + handler, 1)

    # Put ?kill before the handler's unknown-command return.
    insertion = '    if command not in ("?kiss", "?slap"):\n'
    if insertion not in source:
        raise RuntimeError("No encontré el punto de inserción para ?kill.")
    source = source.replace(insertion, KILL_HANDLER + insertion, 1)

    # Add a response button to ?spank, keeping the requested action playful
    # and explicitly non-sexual.
    spank_text = 'description=f"🍑 {message.author.mention} le da una palmadita traviesa a {target.mention}."'
    spank_at = source.find(spank_text)
    if spank_at < 0:
        raise RuntimeError("No encontré el bloque de ?spank.")
    reply_start = source.find("        await message.reply(\n", spank_at)
    reply_end = source.find("        return True", reply_start) if reply_start >= 0 else -1
    if reply_start < 0 or reply_end < 0:
        raise RuntimeError("No encontré la respuesta de ?spank.")
    block = source[reply_start:reply_end]
    if "SpankReturnView(message.author, target)" not in block:
        embed_line = "            embed=embed,\n"
        if embed_line not in block:
            raise RuntimeError("No encontré el embed en la respuesta de ?spank.")
        block = block.replace(embed_line, embed_line + "            view=SpankReturnView(message.author, target),\n", 1)
        source = source[:reply_start] + block + source[reply_end:]

    app_file.write_text(source, encoding="utf-8")


__all__ = ["patch_app_file"]
