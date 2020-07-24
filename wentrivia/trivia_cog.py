from typing import Dict
from discord.ext.commands import Context, Cog
from discord.ext import commands

from .trivia import RegularTrivia


class TriviaCog(Cog):
    """This cog sets the rules to start a new game, supevising what channels
    can games be started in, and how many can be played concurrently."""
    def __init__(self, bot: commands.bot.Bot):
        self.bot = bot
        self.games: Dict[int, RegularTrivia] = {}
        self.channels = [627959873329430570]

    @commands.command()
    async def start(self, ctx: Context) -> None:
        """Starts a new game in the current channel."""
        can_start = (
            ctx.channel.id in self.channels and
            ctx.channel.id not in self.games.keys()
        )

        if not can_start:
            return

        game = RegularTrivia(ctx=ctx)
        self.games[ctx.channel.id] = game
        await game.start()
        del self.games[ctx.channel.id]
