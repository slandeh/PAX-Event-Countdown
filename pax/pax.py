import asyncio

import datetime
from pytz import timezone
from redbot.core import commands, tasks

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
        self.bot = bot
        self.category = self.bot.get_channel(headerCategory)
        self.countdown = ''
        self.countdownDate = None
        self.countdownEvent = None

    def cog_unload(self):
        try:
            self.incrementation_check.cancel() #pylint: disable=no-member

        except:
            pass

    def resolve_secs(self, datetimestamp, _time=False):
        if not _time:
            hours = datetimestamp.hours
            minutes = datetimestamp.minutes
            seconds = datetimestamp.seconds

        else:
            hours = datetimestamp.hour
            minutes = datetimestamp.minute
            seconds = datetimestamp.second

        return (hours * 60 * 60) + (minutes * 60) + seconds


    def in_hours(self):
        currentDate = datetime.datetime.now(tz=eventTzs[self.countdownEvent])
        startDiff = self.countdownDate + currentDate
        currentDateSecs = self.resolve_secs(currentDate)
        startDaySecs = self.resolve_secs(eventStart[self.countdownEvent], True)
        if startDiff.days == eventDays[self.countdownEvent]:
            endDaySecs = self.resolve_secs(eventLastDay[self.countdownEvent], True)

        else:
            endDaySecs = self.resolve_secs(eventEnd[self.countdownEvent], True)

        if startDaySecs < currentDateSecs < endDaySecs:
            return True

        else:
            return False

    @tasks.loop(minutes=1)
    async def incrementation_check(self):
        if not self.countdownDate: return # No date to count towards, ignore
        currentDatetime = datetime.datetime.now(tz=eventTzs[self.countdownEvent])
        dateDiff = self.countdownDate - currentDatetime
        print(self.countdownDate)
        print(currentDatetime)
        print(dateDiff)

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
            oneDaySeconds = ((end.hour * 60 * 60) + end.minute * 60) - ((start.hour * 60 * 60) + start.minute * 60)
            eventSeconds = (oneDaySeconds * (length - 1) + (lastDay.hour * 60 * 60) + lastDay.minute * 60)
            elaspedDays = currentDatetime.day - self.countdownDate.day
            dayDiff = currentDatetime - self.countdownDate
            if elaspedDays == 0:
                # The current day is the same as the event start day
                elaspedSeconds = int(dayDiff.total_seconds())

            else:
                # It is not the first day of the event
                elaspedSeconds = (oneDaySeconds * elaspedDays) + (int(dayDiff.total_seconds()))

            completedPercent = int((elaspedSeconds / eventSeconds) * 100)
            if completedPercent >= 100:
                await self.incrementation_check.clear_exception_types() #pylint: disable=no-member
                self.incrementation_check.stop() #pylint: disable=no-member
                catName = f'PAX {self.countdownEvent.capitalize()}: 100% Complete'

            else:
                catName = f'PAX {self.countdownEvent.capitalize()}: '
                catName +=f'{completedPercent}% Complete'

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

                    else:
                        dayCnt = f'{minutesDiff} minute'

            else:
                dayCnt = f'{dateDiff.days} day'

            catName = f'PAX {self.countdownEvent.capitalize()}: '
            catName += f'⚠ {dayCnt} ⚠' if dateDiff.days <= 7 else f' {dayCnt}'

        if self.countdown == catName: return # No need to edit if it will be the same
        self.countdown = catName
        await self.category.edit(name=catName)

    @commands.command(name='setevent')
    async def _set_event(self, ctx, event, *, date):
        if event.lower() not in eventTzs.keys():
            return await ctx.send(f'Invalid event {event}')

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
        dateDiff = eventDate - datetime.datetime.now(tz=eventTzs[event])
        if dateDiff.days > 1:
            self.countdown = f'{dateDiff.days} days'

        else:
            self.countdown = f'{dateDiff.days} day'

        catName = f'PAX {event.capitalize()}: '
        catName += f'⚠ {self.countdown} ⚠' if dateDiff.days <= 7 else f' {self.countdown}'
        await self.category.edit(name=catName)
        self.incrementation_check.start() #pylint: disable=no-member

def setup(bot):
    print('[PAX] starting')
    bot.add_cog(PAXCountdown(bot))

def teardown(bot):
    print('[PAX] closing')
    bot.remove_cog('PAXCountdown')
