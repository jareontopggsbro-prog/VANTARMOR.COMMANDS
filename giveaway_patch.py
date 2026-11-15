from pathlib import Path
import re

MARKER = "# VANTARMOR_GIVEAWAY_IMPLEMENTATION_V2"
HELPERS = r'''# VANTARMOR_GIVEAWAY_IMPLEMENTATION_V2
class GiveawayView(discord.ui.View):
    """In-memory giveaway entries; no moderation or external side effects."""
    def __init__(self):
        super().__init__(timeout=None)
        self.entries = {}
        self.ended = False

    @discord.ui.button(label="🎉 Participar", style=discord.ButtonStyle.success)
    async def join(self, interaction, button):
        if self.ended:
            await interaction.response.send_message("Este sorteo ya terminó.", ephemeral=True)
            return
        if interaction.user.bot:
            await interaction.response.send_message("Las cuentas bot no pueden participar.", ephemeral=True)
            return
        if interaction.user.id in self.entries:
            self.entries.pop(interaction.user.id)
            text = "Quitaste tu participación."
        else:
            self.entries[interaction.user.id] = interaction.user
            text = "¡Participación registrada! Pulsa otra vez para retirarla."
        await interaction.response.send_message(text, ephemeral=True)

    def close(self):
        self.ended = True
        for item in self.children:
            item.disabled = True


async def finish_giveaway(message, view, winners_count, prize, seconds):
    await asyncio.sleep(seconds)
    view.close()
    participants = list(view.entries.values())
    winners = random.sample(participants, min(winners_count, len(participants))) if participants else []
    embed = discord.Embed(title="🎉 Sorteo terminado", color=discord.Color.blurple())
    embed.add_field(name="Premio", value=prize, inline=False)
    if winners:
        embed.add_field(name="Ganador(es)", value=", ".join(user.mention for user in winners), inline=False)
        embed.description = f"Participantes: **{len(participants)}**"
    else:
        embed.description = "No hubo participantes."
    try:
        await message.edit(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
        if winners:
            await message.reply(
                "🎊 Ganador(es): " + ", ".join(user.mention for user in winners),
                mention_author=False,
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )
    except (discord.Forbidden, discord.HTTPException) as error:
        print(f"No se pudo cerrar el sorteo: {type(error).__name__}")
'''

COMMAND = '''@tree.command(name="sorteo", description="Crea un sorteo en este canal", guild=GUILD)
@app_commands.describe(ganadores="Ganadores (1 a 10)", duracion="10m, 2h, 3d (máximo 30 días)", premio="Premio opcional")
async def giveaway(interaction: discord.Interaction, ganadores: app_commands.Range[int, 1, 10], duracion: str, premio: Optional[str] = None):
    seconds = duration_seconds(duracion)
    if seconds is None or seconds > 30 * 86400:
        await interaction.response.send_message("Duración no válida. Usa `10m`, `2h` o `3d` (máximo 30 días).", ephemeral=True)
        return
    prize = (premio or "Premio sorpresa").strip()
    if not prize or len(prize) > 200:
        await interaction.response.send_message("El premio debe tener entre 1 y 200 caracteres.", ephemeral=True)
        return
    view = GiveawayView()
    embed = discord.Embed(title="🎉 ¡Sorteo!", description=f"**Premio:** {prize}\\n**Ganadores:** {ganadores}\\n**Termina en:** {duracion}\\nPulsa el botón para participar.", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    asyncio.create_task(finish_giveaway(message, view, int(ganadores), prize, seconds))


'''


def patch_app_file(app_file: Path) -> None:
    source = app_file.read_text(encoding="utf-8")
    generated_command = '@tree.command(name="sorteo", description="Crea un sorteo en este canal", guild=GUILD)'

    # Remove the previous generated helper block, if a writable container layer
    # retained it, and remove any old /sorteo implementation without depending
    # on neighboring command names (other patches may replace the cookie block).
    if MARKER in source:
        helper_start = source.index(MARKER)
        command_start = source.find(generated_command, helper_start)
        if command_start >= 0:
            source = source[:helper_start] + source[command_start:]
    source = re.sub(
        r'(?ms)^@tree\.command\(name="sorteo"[^\n]*\)\n.*?(?=^@tree\.command|^@client\.event|\Z)',
        "",
        source,
    )
    if MARKER in source:
        source = re.sub(r'(?ms)^# VANTARMOR_GIVEAWAY_IMPLEMENTATION_V\d+\n.*?(?=^@tree\.command|^@client\.event|\Z)', "", source, count=1)

    # Insert generated helpers/command directly before the message event,
    # which is a stable top-level anchor across the app's transformation patches.
    anchor = "@client.event\nasync def on_message(message):\n"
    if anchor not in source:
        raise RuntimeError("No encontré on_message para instalar el comando /sorteo.")
    source = source.replace(anchor, HELPERS + "\n\n" + COMMAND + anchor, 1)
    app_file.write_text(source, encoding="utf-8")


__all__ = ["patch_app_file"]
