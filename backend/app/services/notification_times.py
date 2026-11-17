"""Custom email delivery times: validation, legacy presets and due checks."""
from datetime import datetime, timedelta
import re
from typing import Iterable, List

MAX_TIMES = 3
# A slot still counts as due for this long after its time, so a short delay
# or a server restart does not make the email go missing.
DUE_WINDOW = timedelta(minutes=10)
LEGACY_PRESETS = {"morning": ["07:00"], "night": ["19:00"], "both": ["07:00", "19:00"]}
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def normalize_times(values: Iterable[str]) -> List[str]:
    """Validate "HH:MM" times; returns them de-duplicated and sorted.
    Raises ValueError for bad values or when not 1 to 3 times are given."""
    times = []
    for value in values:
        value = str(value).strip()
        if not _TIME.match(value):
            raise ValueError(f"Invalid time {value!r}; use 24-hour HH:MM")
        if value not in times:
            times.append(value)
    if not 1 <= len(times) <= MAX_TIMES:
        raise ValueError(f"Choose between 1 and {MAX_TIMES} delivery times")
    return sorted(times)


def user_times(user) -> List[str]:
    """The user's delivery times, falling back to the legacy preset."""
    custom = getattr(user, "email_notification_times", None) or []
    if custom:
        return sorted(custom)
    preset = (getattr(user, "email_notification_schedule", None) or "morning").lower()
    return list(LEGACY_PRESETS.get(preset, LEGACY_PRESETS["morning"]))


def due_times(user, now: datetime) -> List[str]:
    """Times whose slot started within DUE_WINDOW before `now` (an aware
    datetime in the email timezone) and were not already sent today."""
    today = now.date().isoformat()
    sent = getattr(user, "email_notification_last_sent", None) or {}
    due = []
    for value in user_times(user):
        hour, minute = map(int, value.split(":"))
        slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if slot <= now < slot + DUE_WINDOW and sent.get(value) != today:
            due.append(value)
    return due
