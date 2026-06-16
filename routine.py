"""Workout routine scheduling.

A routine decides whether a given calendar day is a WORKOUT day or a REST day.
Two modes, both editable from the UI (no code changes needed to switch):

- 'weekly' : a 7-char pattern indexed by weekday (Mon..Sun), e.g. 'WRWRWRR'
             (a 3-day split = train Mon/Wed/Fri).
- 'cycle'  : a repeating pattern anchored to a start date, e.g. 'WR'
             (alternate days = train 1, rest 1), 'WWRR', etc.
"""
from datetime import date

WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def build_weekly_pattern(workout_weekdays):
    """workout_weekdays: iterable of ints 0..6 (Mon=0). Returns a 7-char W/R string."""
    wd = set(workout_weekdays)
    return ''.join('W' if i in wd else 'R' for i in range(7))


def build_cycle_pattern(work_days, rest_days):
    work_days = max(1, int(work_days or 0))
    rest_days = max(0, int(rest_days or 0))
    return 'W' * work_days + 'R' * rest_days


def is_workout_day(day, mode, pattern, start):
    """day, start: date objects. Returns True if `day` is a scheduled workout day."""
    if not pattern:
        return True
    if mode == 'weekly':
        return pattern[day.weekday() % len(pattern)] == 'W'
    # cycle: index by offset from the anchor date
    offset = (day - start).days
    return pattern[offset % len(pattern)] == 'W'


def parse_weekly(pattern):
    """Weekday indices (0..6) marked as workout in a 7-char weekly pattern."""
    if not pattern:
        return []
    return [i for i, ch in enumerate(pattern[:7]) if ch == 'W']


def parse_cycle(pattern):
    """Split a 'WWRR'-style pattern into (work_days, rest_days). Assumes W's then R's."""
    if not pattern:
        return (1, 1)
    work = pattern.count('W')
    rest = pattern.count('R')
    return (work or 1, rest)


def describe(mode, pattern):
    """Human-readable summary of a routine."""
    if mode == 'weekly':
        days = parse_weekly(pattern)
        if not days:
            return 'No training days set'
        if len(days) == 7:
            return 'Every day'
        names = ', '.join(WEEKDAYS[i] for i in days)
        return f'{len(days)}-day split · {names}'
    work, rest = parse_cycle(pattern)
    if rest == 0:
        return 'Every day'
    return f'Train {work}, rest {rest} (repeating)'
