from pathlib import Path


MARKER = "# VANTARMOR_KILL_ROLEPLAY_BUTTONS_V1"

KILL_VIEW = r'''# VANTARMOR_KILL_ROLEPLAY_BUTTONS_V1
class KillRoleplayView(discord.ui.View):
    """Two fictional, non-graphic roleplay outcomes for the mentioned user."""
    def __init__(self, initiator, recipient):
        super().__init__(timeout=300)
        self.initiator = initiator
        self.recipient = recipient
        self.finished = False

    async def interaction_check(self, interaction):
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("Solo la persona mencionada puede elegir una respuesta.", ephemeral=True)
            return False
        if self.finished:
            await interaction.response.send_message("Esta escena ya terminó.", ephemeral=True)
            return False
        return True

    async def finish(self, interaction, action):
        self.finished = True
        for item in self.children:
            item.disabled = True
        if action == "revenge":
            text = f"💀 {self.recipient.mention} volvió al combate para vengarse de {self.initiator.mention}. *(Roleplay ficticio.)*"
            image = await random_anime_gif("revenge")
        else:
            text = f"👻 {self.recipient.mention} volvió como fantasma para asustar a {self.initiator.mention}. *(Roleplay ficticio.)*"
            image = await random_anime_gif("scare")
        embed = discord.Embed(description=text, color=discord.Color.blurple())
        if image:
            embed.set_image(url=image)
        await interaction.response.edit_message(embed=embed, view=self, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))

    @discord.ui.button(label="💀 Vengar", style=discord.ButtonStyle.danger)
    async def revenge(self, interaction, button):
        await self.finish(interaction, "revenge")

    @discord.ui.button(label="👻 Asustar", style=discord.ButtonStyle.secondary)
    async def scare(self, interaction, button):
        await self.finish(interaction, "scare")
'''


def patch_app_file(app_file: Path) -> None:
    source = app_file.read_text(encoding="utf-8")
    start = source.find("class KillRoleplayView(")
    if start < 0:
        raise RuntimeError("No encontré KillRoleplayView para agregar sus botones.")
    end = source.find("class SpankReturnView(", start)
    if end < 0:
        raise RuntimeError("No encontré el final de KillRoleplayView.")
    source = source[:start] + KILL_VIEW + "\n\n" + source[end:]

    # The GIF helper already accepts arbitrary action keys. Add specific
    # endpoint categories, with empty fallbacks so it never substitutes an
    # unrelated GIF for a revenge or ghost scene.
    if '"revenge":' not in source:
        source = source.replace(
            '    "kill": ("https://nekos.best/api/v2/kick", "https://api.waifu.pics/sfw/kill"),\n',
            '    "kill": ("https://nekos.best/api/v2/kick", "https://api.waifu.pics/sfw/kill"),\n'
            '    "revenge": ("https://nekos.best/api/v2/kick", "https://api.waifu.pics/sfw/kick"),\n'
            '    "scare": ("https://nekos.best/api/v2/scare", "https://api.waifu.pics/sfw/scare"),\n',
            1,
        )
        source = source.replace('    "kill": (),\n', '    "kill": (),\n    "revenge": (),\n    "scare": (),\n', 1)

    source = source.replace("view=KillRoleplayView(target)", "view=KillRoleplayView(message.author, target)")
    app_file.write_text(source, encoding="utf-8")


__all__ = ["patch_app_file"]
