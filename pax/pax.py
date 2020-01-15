import asyncio
import datetime
import logging

from pytz import timezone
from redbot.core import Config, commands
from discord.ext import tasks

# These constants can be moved to a
# settings file and that file can instead
# be imported if you would like to make it
# prettier

headerCategory = 314857672585248769
eventTzs = {
    'east': timezone('America/New_York'),
    'west': timezone('America/Los_Angeles'),
    'south': timezone('America/Chicago'),
    'unplugged': timezone('America/New_York'),
    'aus': timezone('Australia/Melbourne')
}
eventDays = {
    'east': 4,
    'west': 4,
    'south': 3,
    'unplugged': 3,
    'aus': 3
}
eventStart = {
    'east': datetime.time(hour=10, minute=0, tzinfo=eventTzs['east']),
    'west': datetime.time(hour=9, minute=30, tzinfo=eventTzs['west']),
    'south': datetime.time(hour=10, tzinfo=eventTzs['south']),
    'unplugged': datetime.time(hour=10, tzinfo=eventTzs['unplugged']),
    'aus': datetime.time(hour=10, tzinfo=eventTzs['aus'])
}
eventEnd = {
    'east': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['east']),
    'west': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['west']),
    'south': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['south']),
    'unplugged': datetime.time(hour=23, minute=59, second=59, tzinfo=eventTzs['unplugged']),
    'aus': datetime.time(hour=23, tzinfo=eventTzs['aus'])
}
eventLastDay = {
    'east': datetime.time(hour=19, tzinfo=eventTzs['east']),
    'west': datetime.time(hour=19, tzinfo=eventTzs['west']),
    'south': datetime.time(hour=19, tzinfo=eventTzs['south']),
    'unplugged': datetime.time(hour=19, tzinfo=eventTzs['unplugged']),
    'aus': datetime.time(hour=19, tzinfo=eventTzs['aus'])
}
dateFmt = '%Y-%m-%d'

class PAXCountdown(commands.Cog):
    def __init__(self, bot):
        logging.info('[PAX Countdown] Loading cog')
        self.bot = bot
        self.config = Config.get_conf(self, identifier='pax_countdown')
        self.config.register_global({
            'tracked_event': None,
            'admin_role': None
        })
        self.countdown = ''
        self.countdownDate = None
        self.countdownEvent = None

        tracked_event = self.config.tracked_event()
        if tracked_event:
            existing_event = datetime.datetime.strptime(tracked_event['date'], dateFmt)
            existing_event = eventTzs[tracked_event['name']].localize(existing_event.replace(hour=eventStart[tracked_event['name']].hour, minute=eventStart[tracked_event['name']].minute))
            datediff = resolve_secs(existing_event - datetime.datetime.now(tz=eventTzs[tracked_event['name']]), _time=True)

            if datediff >= 0: # Event is set to a future date
                logging.info(f'[PAX Countdown] Found previously set countdown for {tracked_event["name"]}, restoring')
                self.countdownDate = existing_event
                self.countdownEvent = tracked_event['name']
                self.incrementation_check.start() #pylint: disable=no-member

            else: # Event is either on-going, or completely over. Check which
                start = eventStart[tracked_event['name']
                end = eventEnd[tracked_event['name']
                lastDay = eventLastDay[tracked_event['name']
                length = eventDays[tracked_event['name']
                oneDaySeconds = ((end.hour * 60 * 60) + end.minute * 60 + end.second) - ((start.hour * 60 * 60) + start.minute * 60 + start.second)
                eventSeconds = (oneDaySeconds * (length - 1) + ((lastDay.hour - start.hour) * 60 * 60) + (lastDay.minute - start.minute) * 60)

                if eventSeconds > abs(datediff): # Event on-going
                    logging.info(f'[PAX Countdown] Found previously set countdown for {tracked_event["name"]}, restoring')
                    self.countdownDate = existing_event
                    self.countdownEvent = tracked_event['name']
                    self.incrementation_check.start() #pylint: disable=no-member

                else:
                    logging.warning(f'[PAX Countdown] Found previously set count for {tracked_event["name"]} that is already over, discarding')

    def cog_unload(self):
        try:
            self.incrementation_check.cancel() #pylint: disable=no-member

        except:
            pass

    def resolve_secs(self, datetimestamp, _time=False):
        if not _time:
            hours = datetimestamp.hour
            minutes = datetimestamp.minute
            seconds = datetimestamp.second

        else:
            hours = datetimestamp.hours
            minutes = datetimestamp.minutes
            seconds = datetimestamp.seconds

        return (hours * 60 * 60) + (minutes * 60) + seconds


    def in_hours(self):
        currentDate = datetime.datetime.now(tz=eventTzs[self.countdownEvent])
        startDiff = currentDate - self.countdownDate
        currentDateSecs = self.resolve_secs(currentDate)
        startDaySecs = self.resolve_secs(eventStart[self.countdownEvent], True)
        if startDiff.days == eventDays[self.countdownEvent]:
            endDaySecs = self.resolve_secs(eventLastDay[self.countdownEvent], True)

        else:
            endDaySecs = self.resolve_secs(eventEnd[self.countdownEvent], True)

        if startDaySecs < currentDateSecs <= endDaySecs:
            return True

        else:
            return False

    @tasks.loop(seconds=5)
    async def incrementation_check(self):
        if not self.countdownDate: return # No date to count towards, ignore
        currentDatetime = datetime.datetime.now(tz=eventTzs[self.countdownEvent])
        dateDiff = self.countdownDate - currentDatetime
        #print(self.countdownDate)
        print(currentDatetime)
        #print(dateDiff)

        if dateDiff.total_seconds() <= 0: # Event in-progress
            if not self.in_hours():
                print('out of hours')
                return

            print('event live!')
            start = eventStart[self.countdownEvent]
            end = eventEnd[self.countdownEvent]
            lastDay = eventLastDay[self.countdownEvent]
            length = eventDays[self.countdownEvent]

            # We need to do some annoyingly long, but simple math here
            oneDaySeconds = ((end.hour * 60 * 60) + end.minute * 60 + end.second) - ((start.hour * 60 * 60) + start.minute * 60 + start.second)
            #print(f'one day seconds {oneDaySeconds}')
            eventSeconds = (oneDaySeconds * (length - 1) + ((lastDay.hour - start.hour) * 60 * 60) + (lastDay.minute - start.minute) * 60)
            print(f'event seconds {eventSeconds}')
            elaspedDays = currentDatetime.day - self.countdownDate.day
            #print(f'elapsed days {elaspedDays}')
            dayDiff = currentDatetime - self.countdownDate
            #print(f'day diff {dayDiff}')
            elaspedSeconds = ((currentDatetime.hour - start.hour) * 60 * 60) + ((currentDatetime.minute - start.minute) * 60) + (currentDatetime.second - start.second)
            if elaspedDays != 0:
                # The current day is the same as the event start day
                elaspedSeconds += (oneDaySeconds * elaspedDays)

            print(f'elasped seconds {elaspedSeconds}')
            completedPercent = int((elaspedSeconds / eventSeconds) * 100)
            if completedPercent >= 100:
                self.incrementation_check.clear_exception_types() #pylint: disable=no-member
                self.incrementation_check.stop() #pylint: disable=no-member
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
        await self.bot.get_channel(headerCategory).edit(name=catName)

    @commands.command(name='setevent')
    async def _set_event(self, ctx, event, *, date):
        if self.countdownEvent: # Stop the current task loop
            self.incrementation_check.clear_exception_types() #pylint: disable=no-member
            self.incrementation_check.stop() #pylint: disable=no-member

        if event.lower() not in eventTzs.keys():
            return await ctx.send(f'Invalid event `{event}`. One of {", ".join(eventDays.keys())}. Case-insensitive')

        try:
            eventDate = datetime.datetime.strptime(date, dateFmt)
            #eventDate = eventDate.replace(hour=eventStart[event].hour, minute=eventStart[event].minute, tzinfo=eventTzs[event])
            #eventDate = eventTzs[event].normalize(eventDate.replace(hour=eventStart[event].hour, minute=eventStart[event].minute, tzinfo=eventTzs[event]))
            eventDate = eventTzs[event].localize(eventDate.replace(hour=eventStart[event].hour, minute=eventStart[event].minute))

        except ValueError:
            await ctx.message.delete()
            return await ctx.send(f'Invalid datetime `{date}`. Use the format `yyyy-mm-dd`', delete_after=15)

        self.countdownDate = eventDate
        self.countdownEvent = event
        self.incrementation_check.start() #pylint: disable=no-member

        return await ctx.send(f'Success! Now set and tracking **{self.countdownEvent}**, starting on ' + eventDate.strftime('%Y-%m-%d at %H:%M event local time.'))

def setup(bot):
    print('[PAX] starting')
    bot.add_cog(PAXCountdown(bot))

def teardown(bot):
    print('[PAX] closing')
    bot.remove_cog('PAXCountdown')
