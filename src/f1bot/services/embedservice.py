import discord
from src.f1bot.services.models import (
    League,
    GrandPrix,
    Player
)

class EmbedService:
    def __init__(self):
        pass

    @staticmethod
    async def create_draft_success_embed(self, league_obj: League, grand_prix: GrandPrix, draft_info, player_obj: Player) -> discord.Embed:
        d1 = draft_info['driver1']
        d2 = draft_info['driver2']
        d3 = draft_info['driver3']
        wc = draft_info['wildcard']
        cons = draft_info['constructor']

        embed = discord.Embed(title="Draft Succeeded!",
                              description=f"Team drafted for the **{grand_prix.event_name}**!",
                              colour=311122)

        embed.add_field(name=f"{d1.first_name} {d1.last_name}",
                        value=f"Driver 1",
                        inline=True)
        embed.add_field(name=f"{d2.first_name} {d2.last_name}",
                        value=f"Driver 2",
                        inline=True)
        embed.add_field(name=f"{d3.first_name} {d3.last_name}",
                        value=f"Driver 3",
                        inline=True)
        embed.add_field(name=f"{wc.first_name} {wc.last_name}",
                        value=f"🎲Bogey Driver🎲",
                        inline=True)
        embed.add_field(name=f"{cons.full_name}",
                        value=f"🏎️Constructor🏎️",
                        inline=True)

        embed.set_author(name=f"{league_obj.name}")
        embed.set_footer(text=f"{player_obj.username}")
        return embed

    async def create_draft_failure_embed(self, message: str) -> discord.Embed:
        embed = discord.Embed(title="Draft Failed!",
                              description=f"",
                              colour=13895688)
        embed.add_field(name="Reason", value=message, inline=False)
        return embed
    async def create_generic_failure_embed(self, message: str) -> discord.Embed:
        embed = discord.Embed(title="Error!",
                              description=f"{message}",
                              colour=13895688
        )
        return embed