from datetime import datetime, timedelta
from typing import Optional

DAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


def get_next_day_date(day: str) -> Optional[str]:
    """Convert day name to next occurrence date."""
    day = day.lower()
    if day not in DAYS:
        return None

    today = datetime.now()
    target_weekday = DAYS[day]
    days_ahead = target_weekday - today.weekday()

    if days_ahead <= 0:
        days_ahead += 7

    next_day = today + timedelta(days=days_ahead)
    return next_day.strftime("%Y-%m-%d")
