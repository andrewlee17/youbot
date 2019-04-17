import csv
from datetime import datetime, timedelta, timezone

class BossData:
    bosses = []

    def __init__(self, bosses):
        self.bosses = bosses

    @staticmethod
    def loadBossData(file='data/bosses.csv'):
        bosses = []
        # NOTE: This assumes that the bosses are sorted in the csv.
        with open(file, 'r') as bossDataCsv:
            reader = csv.reader(bossDataCsv)
            for row in reader:
                name = row[3]
                day = int(row[0])
                hour = int(row[1])
                minute = int(row[2])

                bosses.append(BossData.Boss(name, day, hour, minute))

        return BossData(bosses)

    class Boss:
        def __init__(self, name, day, hour, minute):
            self.name = name
            self.day = day
            self.hour = hour
            self.minute = minute

class BossCycle:
    tz = timezone(timedelta(hours=2))

    def __init__(self, bossData, startingTimestamp):
        assert(startingTimestamp.tzinfo is not None)
        startingTimestamp = startingTimestamp.astimezone(self.tz)

        self.bossEvents = []
        self.currentBossEvent = 0

        floorMonday = startingTimestamp - timedelta(days = startingTimestamp.weekday())
        floorMonday = datetime(floorMonday.year, floorMonday.month, floorMonday.day, tzinfo = self.tz)

        for boss in bossData.bosses:
            timestamp = floorMonday + timedelta(days = boss.day, hours = boss.hour, minutes = boss.minute)
            self.bossEvents.append(BossCycle.BossEvent(boss, timestamp))

        while(self.current().timestamp < startingTimestamp):
            self.next()

    def next(self):
        self.bossEvents[self.currentBossEvent].timestamp += timedelta(days = 7)
        self.currentBossEvent = (self.currentBossEvent + 1) % len(self.bossEvents)

        return self.bossEvents[self.currentBossEvent]

    def current(self):
        return self.bossEvents[self.currentBossEvent]

    @staticmethod
    def now():
        bossData = BossData.loadBossData()
        return BossCycle(bossData, datetime.now(timezone.utc))

    class BossEvent:
        def __init__(self, boss, timestamp):
            self.boss = boss
            self.timestamp = timestamp
