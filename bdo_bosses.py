import csv
from datetime import datetime, timedelta, timezone

class BossData:
    bosses = []

    def __init__(self, bosses):
        self.bosses = bosses

    @staticmethod
    def load_boss_data(file='data/bosses.csv'):
        bosses = []
        # NOTE: This assumes that the bosses are sorted in the csv.
        with open(file, 'r') as boss_data_csv:
            reader = csv.reader(boss_data_csv)
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
    tz = timezone(timedelta(hours=2), name = 'CEST')

    def __init__(self, boss_data, starting_datetime):
        assert(len(boss_data.bosses) > 3)
        assert(starting_datetime.tzinfo is not None)
        starting_datetime = starting_datetime.astimezone(self.tz)

        self.boss_events = []
        self.current_boss_event = 0

        floorMonday = starting_datetime - timedelta(days = starting_datetime.weekday())
        floorMonday = datetime(floorMonday.year, floorMonday.month, floorMonday.day, tzinfo = self.tz)

        for index, boss in enumerate(boss_data.bosses):
            boss_datetime = floorMonday + timedelta(days = boss.day, hours = boss.hour, minutes = boss.minute)
            self.boss_events.append(BossCycle.BossEvent(index, boss, boss_datetime))

        self.boss_events[len(self.boss_events) - 1].datetime + timedelta(days = -7)
        self.advance_till(starting_datetime)

    def last(self):
        return self.boss_events[(self.current_boss_event - 1) % len(self.boss_events)]

    def next(self, pos = 0):
        return self.boss_events[(self.current_boss_event + pos) % len(self.boss_events)]

    def advance_till(self, datetime):
        assert(datetime.tzinfo is not None)
        datetime = datetime.astimezone(self.tz)

        while(self.next().datetime < datetime):
            self.advance()
        return self.next()

    def advance(self):
        last_event_index = (self.current_boss_event - 1) % len(self.boss_events)
        last_event = self.boss_events[last_event_index]
        new_last_event = BossCycle.BossEvent(last_event.id + len(self.boss_events),
            last_event.boss, last_event.datetime + timedelta(days = 7))
        self.boss_events[last_event_index] = new_last_event

        self.current_boss_event = (self.current_boss_event + 1) % len(self.boss_events)
        return self.boss_events[self.current_boss_event]

    def now(self):
        return datetime.now(self.tz)

    @staticmethod
    def new_from_now():
        boss_data = BossData.load_boss_data()
        return BossCycle(boss_data, datetime.now(timezone.utc))

    class BossEvent:
        def __init__(self, id, boss, datetime):
            self.id = id
            self.boss = boss
            self.datetime = datetime
