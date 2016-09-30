voice_id = "164936005328044032"
text_id = "231105748791197697"

import discord
import requests
from queue import *
from furl import furl
from discord.ext import commands
import asyncio

class Sona:
    def __init__(self, bot, loop=None):
        self.bot = bot
        self.q = Queue(10)
        self.vote = set()
        self.reset_vote = set()
        self.voice = None
        self.text = None
        self.current = None
        self.loop = loop or asyncio.get_event_loop()
        self.is_playing = False

    async def on_ready(self):
        self.voice = await self.bot.join_voice_channel(discord.Object(id=voice_id))
        self.text = discord.Object(id=text_id)

    def play_next(self):
        if self.q.empty():
            self.current = None
            self.is_playing = False
        else:
            self.current = self.q.get()
            name = self.current['name']
            coro = self.bot.send_message(self.text,'Now playing: **{}**'.format(name))
            fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
            try:
                fut.result(1)
            except:
                pass
            self.current['player'].start()

    @commands.command(pass_context=True, no_pm=True)
    async def add(self, ctx, url : str):
        """Add a song to the queue. Only accepts youtube links."""
        print("Adding {}".format(url))
        audience = set(ctx.message.server.get_channel(voice_id).voice_members)
        if ctx.message.author not in audience:
            await self.bot.say('You must be in the voice channel to **!add**')
        elif self.q.full():
            await self.bot.say("The queue is full! Please wait for a spot to open up.")
        elif url.startswith('https://www.youtube.com/'):
            url_data = furl(url)
            video_id = url_data.args['v']
            payload = {
                'id': video_id,
                'key': 'AIzaSyCFScSe7-VSbBgFXFqxdgdylSujanFXhKg',
                'part': 'snippet'
            }
            r = requests.get("https://www.googleapis.com/youtube/v3/videos", params=payload).json()
            name = r['items'][0]['snippet']['title']
            url = 'https://www.youtube.com/watch?v=' + video_id
            player = await self.voice.create_ytdl_player(url, after=self.play_next)
            player.volume = 0.5
            self.q.put({'name': name, 'by': ctx.message.author, 'player': player })
            await self.bot.say('**{}** has added **{}** to the queue!'.format(ctx.message.author, name))
        else:
            await self.bot.say("Oops. Please make sure you are using the right syntax: **!add *youtubelink***.")

    @commands.command(no_pm=True)
    async def list(self):
        """List songs in the queue."""
        if self.q.empty():
            await self.bot.say("The queue is empty! Add to the queue with **!add *youtubelink***.")
        else:
            s = map(lambda il: str(il[0]+1) + '. ' + il[1]['name'], enumerate(list(self.q.queue)))
            await self.bot.say('\n'.join(s))

    @commands.command(pass_context=True, no_pm=True)
    async def cancel(self, ctx, idx: str):
        """Cancel a song you requested, while it's in the queue. Enter the index of the song in the queue."""
        audience = set(ctx.message.server.get_channel(voice_id).voice_members)
        if ctx.message.author not in audience:
            await self.bot.say('You must be in the voice channel to **!cancel**')
        else:
            try:
                index = int(idx)-1
                newList = list(self.q.queue)
                if index < 0 or index >= len(newList):
                    await self.bot.say("The index is invalid. Try checking with **!list**.")
                elif newList[index]['by'] == ctx.message.author:
                    name = newList[index]['name']
                    del newList[index]
                    self.q.queue = newList
                    await self.bot.say('**{}** cancelled **{}** from the queue.'.format(ctx.message.author, name))
                else:
                    name = newList[index]['name']
                    await self.bot.say('You do not have permission to cancel **{}** from the queue. You can only cancel your own submissions'.format(name))
            except ValueError:
                await self.bot.say("Oops. Please make sure you are using the right syntax: **!cancel *index-number***")

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx):
        """Play music."""
        audience = set(ctx.message.server.get_channel(voice_id).voice_members)
        if ctx.message.author not in audience:
            await self.bot.say('You must be in the voice channel to **!play**')
        elif self.is_playing:
            await self.bot.say("I'm already playing!")
        elif self.current is not None:
            self.is_playing = True
            await self.bot.say('Resuming: **{}**.'.format(self.current['name']))
            self.current['player'].resume()
        elif self.q.empty():
            await self.bot.say('Queue is empty. Add songs to the queue by typing: **!add *youtubelink***.')
        else:
            self.is_playing = True
            self.play_next()

    @commands.command(pass_context=True,no_pm=True)
    async def pause(self, ctx):
        """Pause the song. Enter the play command to resume."""
        audience = set(ctx.message.server.get_channel(voice_id).voice_members)
        if ctx.message.author not in audience:
            await self.bot.say('You must be in the voice channel to **!pause**')
        elif self.is_playing:
            self.is_playing = False
            await self.bot.say('Pausing: **{}**.'.format(self.current['name']))
            self.current['player'].pause()
        else:
            await self.bot.say("Nothing is playing right now!")

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip a song. The number of voters must exceed half the number of people in the channel."""
        audience = set(ctx.message.server.get_channel(voice_id).voice_members)
        if ctx.message.author not in audience:
            await self.bot.say('You must be in the voice channel to **!skip**')
        elif len(self.vote) == 0:
            self.vote.add(ctx.message.author)
            if len(self.vote) * 2 > len(audience)-1:
                self.vote = set()
                await self.bot.say('Skipping: **{}**.'.format(self.current['name']))
                self.current['player'].stop()
            else:
                await self.bot.say('**{}** has voted to skip **{}** from the queue. The song will be skipped when more than half have entered **!skip**.'.format(ctx.message.author, self.current['name']))
        else:
            if ctx.message.author in self.vote:
                await self.bot.say("You have already voted!")
            else:
                self.vote.add(ctx.message.author)
                if len(self.vote) * 2 > len(audience)-1:
                    self.vote = set()
                    await self.bot.say('Skipping: **{}**.'.format(self.current['name']))
                    self.current['player'].stop()
                else:
                    await self.bot.say('**{}** has voted to skip **{}** from the queue. The song will be skipped when more than half have entered **!skip**.'.format(ctx.message.author, name))

    @commands.command(pass_context=True, no_pm=True)
    async def reset(self, ctx):
        """Reset the queue. Deletes all songs in the queue."""
        audience = set(ctx.message.server.get_channel(voice_id).voice_members)
        if ctx.message.author not in audience:
            await self.bot.say('You must be in the voice channel to **!skip**')
        elif self.q.empty():
            await self.bot.say('The playlist is already empty.')
        elif len(self.reset_vote) == 0:
            audience = set(ctx.message.server.get_channel(voice_id).voice_members)
            self.reset_vote.add(ctx.message.author)
            if len(self.reset_vote) * 2 > len(audience)-1:
                self.reset_vote = set()
                self.q = Queue(10)
                await self.bot.say('*Poof.* The playlist is empty.')
            else:
                await self.bot.say('**{}** has voted to reset the playlist. The playlist will be erased when more than half have entered **!reset**.'.format(ctx.message.author))
        else:
            if ctx.message.author in self.vote:
                await self.bot.say("You have already voted!")
            else:
                audience = set(ctx.message.server.get_channel(voice_id).voice_members)
                self.reset_vote.add(ctx.message.author)
                if len(self.reset_vote) * 2 > len(audience)-1:
                    self.reset_vote = set()
                    await self.bot.say('*Poof.* The playlist is empty.')
                else:
                    await self.bot.say('**{}** has voted to reset the playlist. The playlist will be erased when more than half have entered **!reset**.'.format(ctx.message.author))


bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'))
bot.remove_command('help')
bot.add_cog(Sona(bot))

bot.run(token)
