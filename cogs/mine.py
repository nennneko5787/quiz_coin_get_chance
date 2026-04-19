from typing import Optional

import discord
from discord.ext import commands, tasks


class MineCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dailyCommand: Optional[discord.SlashCommand] = None
        self.mineCommand: Optional[discord.SlashCommand] = None
        self.workCommand: Optional[discord.SlashCommand] = None

    async def cog_load(self):
        self.mine.start()
        self.work.start()
        self.daily.start()

    @tasks.loop(hours=24)
    async def daily(self):
        guild = self.bot.get_guild(1491704145608966203)
        if not guild:
            return
        channel = guild.get_channel(1493537253476007946)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        if not self.dailyCommand:
            commands = await guild.application_commands()
            for command in commands:
                if command.name == "daily" and isinstance(
                    command, discord.SlashCommand
                ):
                    self.dailyCommand = command
                    break
        if self.dailyCommand:
            await self.dailyCommand(channel)

    @tasks.loop(hours=1)
    async def work(self):
        guild = self.bot.get_guild(1491704145608966203)
        if not guild:
            return
        channel = guild.get_channel(1493537253476007946)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        if not self.workCommand:
            commands = await guild.application_commands()
            for command in commands:
                if command.name == "work" and isinstance(command, discord.SlashCommand):
                    self.workCommand = command
                    break
        if self.workCommand:
            await self.workCommand(channel)

    @tasks.loop(seconds=31)
    async def mine(self):
        guild = self.bot.get_guild(1491704145608966203)
        if not guild:
            return
        channel = guild.get_channel(1493537253476007946)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        if not self.mineCommand:
            commands = await guild.application_commands()
            for command in commands:
                if command.name == "mine" and isinstance(command, discord.SlashCommand):
                    self.mineCommand = command
                    break
        if self.mineCommand:
            await self.mineCommand(channel)


async def setup(bot: commands.Bot):
    await bot.add_cog(MineCog(bot))
