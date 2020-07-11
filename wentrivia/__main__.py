import os
from discord.ext import commands

from wentrivia.trivia_cog import TriviaCog

bot = commands.Bot(command_prefix='!')
bot.add_cog(TriviaCog(bot))

token = os.environ.get('TRIVIA_BOT_TOKEN')

if token is None:
    print("TRIVIA_BOT_TOKEN hasn't been set!")
else:
    bot.run(token)
