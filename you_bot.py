from bdo_bosses import BossCycle
from datetime import datetime, timedelta
from collections import deque
import discord
import asyncio
import sys

_STATUS_CONTENT = 'YouBot - World Boss Timers'
_TABLE_IMAGE = 'https://i.imgur.com/oiX3KdS.png'
_BOSS_CHANNEL = "bdo-boss-timers"
_SPAWN_RETENTION_THRESHOLD = timedelta(minutes = -14, seconds = 30)
_WARNING_THRESHOLD = timedelta(minutes = 15, seconds = 30)
_SPAWN_THRESHOLD = timedelta(seconds = 30)
_MESSAGE_EXPIRATION = timedelta(minutes = 15)
_NUMBER_OF_UPCOMING_BOSSES = 5

class YouBot(discord.Client):
    guild_clients = []
    current_status_message = None
    current_status_datetime = None
    last_warning = -1
    last_spawn = -1
    expiring_messages = deque()

    def __init__(self, bossCycle):
        self.boss_cycle = bossCycle
        discord.Client.__init__(self)

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user), flush=True)

        for guild in self.guilds:
            await self.init_guild(guild)

        loop = asyncio.get_event_loop()
        loop.create_task(self.update_loop())

    async def on_guild_join(self, guild):
        await self.init_guild(guild)

    async def update_loop(self):
        while True:
            await self.check_expiring_messages()
            await self.update_status()

            time_now = datetime.now()
            next_second = time_now - timedelta(minutes = -1, seconds = time_now.second, microseconds = time_now.microsecond)
            delta = next_second - time_now
            await asyncio.sleep(delta.total_seconds())

    async def update_status(self, update=True):
        global _SPAWN_RETENTION_THRESHOLD, _WARNING_THRESHOLD, _SPAWN_THRESHOLD, _NUMBER_OF_UPCOMING_BOSSES

        current_time = self.boss_cycle.now()
        self.boss_cycle.advance_till(current_time)

        upcoming_bosses = []

        for pos in range(-1, _NUMBER_OF_UPCOMING_BOSSES + 1):
            boss_event = self.boss_cycle.next(pos)
            time_till_spawn = boss_event.datetime - current_time

            if time_till_spawn < _SPAWN_RETENTION_THRESHOLD:
                continue

            if time_till_spawn < _SPAWN_THRESHOLD:
                if self.last_spawn < boss_event.id:
                    self.last_spawn = boss_event.id
                    await self.send_expiring_message('{0.name} has spawned!'.format(boss_event.boss), current_time)

            elif time_till_spawn < _WARNING_THRESHOLD:
                if self.last_warning < boss_event.id:
                    self.last_warning = boss_event.id
                    await self.send_expiring_message('{0.name} will spawn soon!'.format(boss_event.boss), current_time)

            upcoming_bosses.append({'boss_event': boss_event, 'time_till_spawn': time_till_spawn})

        new_status_message = '```md\n'
        new_status_message += "".join(map(lambda boss: _boss_format(boss['boss_event'], boss['time_till_spawn']), upcoming_bosses))
        new_status_message += '```'

        await self.change_presence(activity = discord.Game(name = _compact_boss_format(upcoming_bosses[0]['boss_event'], upcoming_bosses[0]['time_till_spawn'])))

        self.current_status_message = new_status_message
        self.current_status_datetime = current_time

        for guild_client in self.guild_clients:
            await guild_client.update_status(self.current_status_message,
                self.current_status_datetime)

    async def check_expiring_messages(self):
        time_now = self.boss_cycle.now()
        while len(self.expiring_messages) > 0 and self.expiring_messages[0]['expiration'] < time_now:
            expiring_message = self.expiring_messages.popleft()

            for message in expiring_message['messages']:
                await message.delete()

    async def send_expiring_message(self, message, time_now):
        global _MESSAGE_EXPIRATION

        expiration = time_now + _MESSAGE_EXPIRATION
        messages = []

        for guild_client in self.guild_clients:
            message = await guild_client.send_message(message)

            if message is not None:
                messages.append(message)

        self.expiring_messages.append({'expiration': expiration, 'messages': messages})

    async def init_guild(self, guild):
        print('Initializing on {0.name} guild!'.format(guild), flush=True)

        guild_client = YouBot.GuildClient(self, guild)
        await guild_client.init()

        if self.current_status_message is not None:
            await guild_client.update_Status(self.current_status_message,
                self.current_status_datetime)

        self.guild_clients.append(guild_client)

    class GuildClient:
        def __init__(self, client, guild):
            global _BOSS_CHANNEL

            self.client = client
            self.guild = guild
            self.channel = None
            self.status_message = None

            for text_channel in guild.text_channels:
                if text_channel.name == _BOSS_CHANNEL:
                    self.channel = text_channel
                    break

        async def init(self):
            # TODO: Clean old messages
            if self.channel is None:
                return

            await self.channel.purge(check = lambda message: message.author == self.client.user)

        async def update_status(self, status, datetime):
            global _STATUS_CONTENT, _TABLE_IMAGE

            if self.channel is None:
                return

            embed = discord.Embed(title = 'Current server time: {0}'.format(datetime.strftime('%A %I:%M %p %Z')), description = status)

            if self.status_message is None:
                self.status_message = await self.channel.send(content = _STATUS_CONTENT, embed = embed)
                await self.channel.send(embed = discord.Embed().set_image(url = _TABLE_IMAGE))
            else:
                await self.status_message.edit(embed = embed)

        async def send_message(self, message):
            if self.channel is None or self.status_message is None:
                return None

            return await self.channel.send(content = message)

def _compact_boss_format(event, timedelta_format):
    return '[{1}] {0.name}'.format(event.boss, _compact_format_time_delta(timedelta_format))

def _boss_format(event, timedelta_format):
    str_format = '< {0.name} >\n[{1}]({2})\n\n'
    if (timedelta_format < timedelta()):
        str_format = '< {0.name} > <SPAWNED>\n[{1}]({2})\n\n'
    return str_format.format(event.boss,
        event.datetime.strftime('%a %I:%M %p %Z'), _format_time_delta(timedelta_format))

def _compact_format_time_delta(timedelta_format):
    negative = timedelta_format < timedelta()
    if negative:
        timedelta_format = -timedelta_format

    total_minutes = int(timedelta_format.total_seconds() / 60)
    hours, minutes = divmod(total_minutes, 60)

    formatted_delta = ''
    if negative:
        formatted_delta += '-'

    if hours > 0:
        formatted_delta += '{0}h'.format(hours)
    formatted_delta += '{0}m'.format(minutes)

    return formatted_delta

def _format_time_delta(timedelta_format):
    negative = timedelta_format < timedelta()
    if negative:
        timedelta_format = -timedelta_format

    total_minutes = int(timedelta_format.total_seconds() / 60)
    hours, minutes = divmod(total_minutes, 60)

    formatted_delta = ''
    if hours > 1:
        formatted_delta += '{0} hours and '.format(hours)
    elif hours == 1:
        formatted_delta += '1 hour and '

    if minutes != 1:
        formatted_delta += '{0} minutes'.format(minutes)
    else:
        formatted_delta += '1 minute'

    if negative:
        formatted_delta += ' ago'

    return formatted_delta

bossCycle = BossCycle.new_from_now()
client = YouBot(bossCycle)
client.run(sys.argv[1])
