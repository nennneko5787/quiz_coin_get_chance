import os

import dotenv
from discord.ext import commands

dotenv.load_dotenv()

bot = commands.Bot("#", help_command=None)


@bot.event
async def setup_hook():
    await bot.load_extension("cogs.mine")
    await bot.load_extension("cogs.quiz")


bot.run(os.getenv("discord") or "")
