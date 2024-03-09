import asyncio
import datetime
import logging

from pytz import timezone
from redbot.core import Config, commands, checks
from discord.ext import tasks
from discord import channel

# These constants can be moved to a
# settings file and that file can instead
# be imported to make it prettier in the
# future and support updates

eventTzs = {
    'east': timezone('America/New_York'),
    'west': timezone('America/Los_Angeles'),
    'south': timezone('America/Chicago'),
    'unplugged': timezone('America/New_York'),
    'aus': timezone('Australia/Melbourne'),
    'online': timezone('America/Los_Angeles')
}
eventDays = {
    'east': 4,
    'west': 4,
    'south': 3,
    'unplugged': 3,
    'aus': 3,
    'online': 9
}
eventStart = {
    'east': datetime.time(hour=10, minute=0, tzinfo=eventTzs['east']),
    'west': datetime.time(hour=9, minute=30, tzinfo=eventTzs['west']),
    'south': datetime.time(hour=10, tzinfo=eventTzs['south']),
    'unplugged': datetime.time(hour=10, tzinfo=eventTzs['unplugged']),
    'aus': datetime.time(hour=10, tzinfo=eventTzs['aus']),
    'online': datetime.time(hour=11, minute=30, tzinfo=eventTzs['online'])
}
eventEnd = {
    'east': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['east']),
    'west': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['west']),
    'south': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['south']),
    'unplugged': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['unplugged']),
    'aus': datetime.time(hour=23, tzinfo=eventTzs['aus']),
    'online': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['online'])
}
eventLastDay = {
    'east': datetime.time(hour=18, tzinfo=eventTzs['east']),
    'west': datetime.time(hour=18, tzinfo=eventTzs['west']),
    'south': datetime.time(hour=18, tzinfo=eventTzs['south']),
    'unplugged': datetime.time(hour=18, tzinfo=eventTzs['unplugged']),
    'aus': datetime.time(hour=18, tzinfo=eventTzs['aus']),
    'online': datetime.time(hour=19, minute=45, tzinfo=eventTzs['online'])
}
dateFmt = '%Y-%m-%d'
LOG_FORMAT = '%(levelname)s [%(asctime)s]: %(message)s'
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

class PAXCountdown(commands.Cog):
    def __init__(self, bot):
        logging.info('[PAX Countdown] Loading cog')
        self.bot = bot
        self.config = Config.get_conf(self, identifier='paxcountdown')
        default_global = {
            'tracked_event': None,
            'voice_channel': None
        }
        self.config.register_global(**default_global)
        self.countdown = ''
        self.countdownDate = None
        self.countdownEvent = None
        self.check_prior_events.start() #pylint: disable=no-member

        logging.info('[PAX Countdown] Successfully loaded')

    def cog_unload(self):
        try:
            self.incrementation_check.cancel() #pylint: disable=no-member

        except:
            pass

        logging.info('[PAX Countdown] Successfully unloaded')

    def resolve_secs(self, datetimestamp, _time=False):
        if not _time:
            hours = datetimestamp.hour
            minutes = datetimestamp.minute
            seconds = datetimestamp.second
            return (hours * 60 * 60) + (minutes * 60) + seconds

        else:
            seconds = datetimestamp.seconds if datetimestamp.days > 0 else datetimestamp.seconds * -1
            return (datetimestamp.days * 3600) + seconds

    def in_hours(self):
        currentDate = datetime.datetime.now(tz=eventTzs[self.countdownEvent])
        startDiff = currentDate - self.countdownDate
        currentDateSecs = self.resolve_secs(currentDate)
        startDaySecs = self.resolve_secs(eventStart[self.countdownEvent])
        if startDiff.days == eventDays[self.countdownEvent]:
            endDaySecs = self.resolve_secs(eventLastDay[self.countdownEvent])

        else:
            endDaySecs = self.resolve_secs(eventEnd[self.countdownEvent])

        if startDaySecs < currentDateSecs <= endDaySecs:
            return True

        else:
            return False

    @tasks.loop(count=1)
    async def check_prior_events(self):
        self.headerCategory = await self.config.voice_channel()
        await self.bot.wait_until_ready()
        tracked_event = await self.config.tracked_event()
        if tracked_event:
            existing_event = datetime.datetime.strptime(tracked_event['date'], dateFmt)
            existing_event = eventTzs[tracked_event['name']].localize(existing_event.replace(hour=eventStart[tracked_event['name']].hour, minute=eventStart[tracked_event['name']].minute))
            datediff = self.resolve_secs(existing_event - datetime.datetime.now(tz=eventTzs[tracked_event['name']]), _time=True)

            if datediff >= 0: # Event is set to a future date
                logging.info(f'[PAX Countdown] Found previously set countdown for {tracked_event["name"]}, restoring')
                self.countdownDate = existing_event
                self.countdownEvent = tracked_event['name']
                self.incrementation_check.start() #pylint: disable=no-member

            else: # Event is either on-going, or completely over. Check which
                start = eventStart[tracked_event['name']]
                end = eventEnd[tracked_event['name']]
                lastDay = eventLastDay[tracked_event['name']]
                length = eventDays[tracked_event['name']]

                end_date = existing_event + datetime.timedelta(days=length - 1)
                end_date = end_date.replace(hour=lastDay.hour, minute=lastDay.minute)
                if end_date > datetime.datetime.now(tz=eventTzs[tracked_event['name']]):
                    logging.info(f'[PAX Countdown] Found previously set countdown for {tracked_event["name"]}, restoring')
                    self.countdownDate = existing_event
                    self.countdownEvent = tracked_event['name']
                    self.incrementation_check.start() #pylint: disable=no-member

                else:
                    logging.warning(f'[PAX Countdown] Found previously set countdown for {tracked_event["name"]} that is already over, discarding')
                    await self.config.tracked_event.set(None)

    @tasks.loop(minutes=5)
    async def incrementation_check(self):
        await self.bot.wait_until_ready()
        if not self.countdownDate: return # No date to count towards, ignore
        currentDatetime = datetime.datetime.now(tz=eventTzs[self.countdownEvent])
        dateDiff = self.countdownDate - currentDatetime

        if dateDiff.total_seconds() <= 0: # Event in-progress
            if not self.in_hours():
                return

            start = eventStart[self.countdownEvent]
            end = eventEnd[self.countdownEvent]
            lastDay = eventLastDay[self.countdownEvent]
            length = eventDays[self.countdownEvent]

            # We need to do some annoyingly long, but simple math here
            oneDaySeconds = ((end.hour * 60 * 60) + end.minute * 60 + end.second) - ((start.hour * 60 * 60) + start.minute * 60 + start.second)
            eventSeconds = (oneDaySeconds * (length - 1) + ((lastDay.hour - start.hour) * 60 * 60) + (lastDay.minute - start.minute) * 60)
            elaspedDays = currentDatetime.day - self.countdownDate.day
            dayDiff = currentDatetime - self.countdownDate
            elaspedSeconds = ((currentDatetime.hour - start.hour) * 60 * 60) + ((currentDatetime.minute - start.minute) * 60) + (currentDatetime.second - start.second)
            if elaspedDays != 0:
                # The current day is the same as the event start day
                elaspedSeconds += (oneDaySeconds * elaspedDays)

            completedPercent = int((elaspedSeconds / eventSeconds) * 100)
            if completedPercent >= 100:
                self.incrementation_check.clear_exception_types() #pylint: disable=no-member
                self.incrementation_check.stop() #pylint: disable=no-member
                await self.config.tracked_event.set(None)
                catName = f'PAX {self.countdownEvent.capitalize()}: 100% Complete'

            else:
                catName = f'PAX {self.countdownEvent.capitalize()}: '
                catName += f'{completedPercent}% Complete' if completedPercent > 0 else 'Welcome Home'

        else:
            if dateDiff.days > 1:
                dayCnt = f'{dateDiff.days} days'

            elif dateDiff.days == 0:
                hoursDiff = int(dateDiff.seconds / (60 * 60))
                if hoursDiff > 1:
                    dayCnt = f'{hoursDiff} hours'

                elif hoursDiff == 1:
                    dayCnt = f'{hoursDiff} hour'

                else:
                    minutesDiff = round(dateDiff.seconds / 60)
                    if minutesDiff > 1:
                        dayCnt = f'{minutesDiff} minutes'

                    elif minutesDiff == 1:
                        dayCnt = f'{minutesDiff} minute'

                    else:
                        dayCnt = f'{dateDiff.seconds} seconds'

            else:
                dayCnt = f'{dateDiff.days} day'

            catName = f'PAX {self.countdownEvent.capitalize()}: '
            catName += f'⚠ {dayCnt} ⚠' if dateDiff.days <= 7 else f' {dayCnt}'

        if self.countdown == catName: return # No need to edit if it will be the same
        self.countdown = catName
        await self.bot.get_channel(self.headerCategory).edit(name=catName)

    @checks.mod()
    @commands.group(name='pax', invoke_without_command=True)
    async def _pax(self, ctx):
        return

    @checks.mod()
    @_pax.command(name='channel')
    async def _pax_channel(self, ctx, channel: int):
        bot_channel = self.bot.get_channel(channel)
        if not bot_channel: # Invalid channel. Likely not shared server
            return await ctx.send('Unable to set that channel. Make sure to set a channel in a guild I also share')

        await self.config.voice_channel.set(channel)
        self.headerCategory = channel
        return await ctx.send(f'Successfully set `{bot_channel.name}` as the countdown channel')

    @checks.mod()
    @_pax.command(name='stop')
    async def _stop_event(self, ctx):
        if not self.countdownEvent:
            return await ctx.send('Not currently tracking any event, no changes have been made')

        event = self.countdownEvent

        self.incrementation_check.clear_exception_types() #pylint: disable=no-member
        self.incrementation_check.cancel() #pylint: disable=no-member
        self.countdownEvent = None
        self.countdownDate = None
        await self.config.tracked_event.set(None)
        await self.bot.get_channel(self.headerCategory).edit(name='See you next time')

        return await ctx.send(f'Successfully stopped tracking pax {event}')

    @checks.mod()
    @_pax.command(name='event')
    async def _set_event(self, ctx, event, *, date):
        if self.countdownEvent: # Stop the current task loop
            self.incrementation_check.clear_exception_types() #pylint: disable=no-member
            self.incrementation_check.cancel() #pylint: disable=no-member

        if not await self.config.voice_channel():
            return await ctx.send(f'No channel has been set for the countdown timer. Please use the `{ctx.clean_prefix}pax channel [channel]` command to set one. Channel should be an ID')

        if event.lower() not in eventTzs.keys():
            return await ctx.send(f'Invalid event `{event}`. One of {", ".join(eventDays.keys())}. Case-insensitive')

        try:
            eventDate = datetime.datetime.strptime(date, dateFmt)
            eventDate = eventTzs[event].localize(eventDate.replace(hour=eventStart[event].hour, minute=eventStart[event].minute))

        except ValueError:
            await ctx.message.delete()
            return await ctx.send(f'Invalid datetime `{date}`. Use the format `yyyy-mm-dd`', delete_after=15)

        await self.config.tracked_event.set({'name': event.lower(), 'date': date})

        self.countdownDate = eventDate
        self.countdownEvent = event.lower()
        self.incrementation_check.start() #pylint: disable=no-member

        return await ctx.send(f'Success! Now set and tracking **{self.countdownEvent}**, starting on ' + eventDate.strftime('%Y-%m-%d at %H:%M event local time.'))

def setup(bot):
    bot.add_cog(PAXCountdown(bot))

def teardown(bot):
    bot.remove_cog('PAXCountdown')
