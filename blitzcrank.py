import discord
from discord.ext import commands

class Blitzcrank:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True)
    async def help(self):
        with open('commands.txt') as commands:
            await self.bot.say(commands.read())

    @commands.command(no_pm=True)
    async def announcements(self):
        with open('announcements.txt') as a:
            await self.bot.say(a.read())

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'))
bot.remove_command('help')
bot.add_cog(Blitzcrank(bot))

bot.run(token)
