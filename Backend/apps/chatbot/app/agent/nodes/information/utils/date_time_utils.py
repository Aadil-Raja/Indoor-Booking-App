"""
Date and time normalization utilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Karachi")

_DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _is_iso_date(date_str: str) -> bool:
    """Check if a string is a valid ISO date (YYYY-MM-DD)."""
    if not date_str or len(date_str) != 10:
        return False
    try:
        datetime.fromisoformat(date_str)
        return True
    except (ValueError, TypeError):
        return False


def _floor_time_to_hour(time_str: str, chat_id: str) -> str:
    """
    Floor time to nearest hour (round down) if minutes are specified.
    Normalizes raw hour numbers to HH:00 format.

    Examples:
        "1:45" → "01:00", "18:00" → "18:00", "6" → "06:00"
    """
    try:
        if ":" not in time_str:
            try:
                hour = int(time_str)
                if 0 <= hour <= 23:
                    normalized = f"{hour:02d}:00"
                    logger.info(f"Normalized raw hour '{time_str}' → '{normalized}' for chat {chat_id}")
                    return normalized
                logger.warning(f"Invalid hour value '{time_str}' for chat {chat_id}")
            except ValueError:
                logger.warning(f"Could not parse raw hour '{time_str}' for chat {chat_id}")
            return time_str

        for fmt in ["%H:%M", "%I:%M", "%H:%M:%S", "%I:%M:%S"]:
            try:
                parsed = datetime.strptime(time_str, fmt)
                floored = f"{parsed.hour:02d}:00"
                if floored != time_str:
                    logger.info(f"Floored start_time '{time_str}' → '{floored}' for chat {chat_id}")
                return floored
            except ValueError:
                continue

        logger.warning(f"Could not parse time '{time_str}' for flooring in chat {chat_id}")
        return time_str
    except Exception as e:
        logger.error(f"Error flooring time '{time_str}' for chat {chat_id}: {e}")
        return time_str


def _ceil_time_to_hour(time_str: str, chat_id: str) -> str:
    """
    Ceil time to nearest hour (round up) if minutes are specified.
    Normalizes raw hour numbers to HH:00 format.

    Examples:
        "1:45" → "02:00", "18:00" → "18:00", "7" → "07:00"
    """
    try:
        if ":" not in time_str:
            try:
                hour = int(time_str)
                if 0 <= hour <= 23:
                    normalized = f"{hour:02d}:00"
                    logger.info(f"Normalized raw hour '{time_str}' → '{normalized}' for chat {chat_id}")
                    return normalized
                logger.warning(f"Invalid hour value '{time_str}' for chat {chat_id}")
            except ValueError:
                logger.warning(f"Could not parse raw hour '{time_str}' for chat {chat_id}")
            return time_str

        for fmt in ["%H:%M", "%I:%M", "%H:%M:%S", "%I:%M:%S"]:
            try:
                parsed = datetime.strptime(time_str, fmt)
                if parsed.minute > 0 or parsed.second > 0:
                    ceiled = f"{(parsed.hour + 1) % 24:02d}:00"
                    logger.info(f"Ceiled end_time '{time_str}' → '{ceiled}' for chat {chat_id}")
                    return ceiled
                return f"{parsed.hour:02d}:00"
            except ValueError:
                continue

        logger.warning(f"Could not parse time '{time_str}' for ceiling in chat {chat_id}")
        return time_str
    except Exception as e:
        logger.error(f"Error ceiling time '{time_str}' for chat {chat_id}: {e}")
        return time_str


def _get_next_weekday(from_date, day_name: str, chat_id: str) -> Optional[str]:
    """Get the next occurrence of a weekday from a given date."""
    day_name_lower = day_name.lower()
    if day_name_lower not in _DAY_MAP:
        logger.warning(f"Unknown day name '{day_name}' for chat {chat_id}")
        return None

    target = _DAY_MAP[day_name_lower]
    days_ahead = target - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7

    result = (from_date + timedelta(days=days_ahead)).isoformat()
    logger.info(f"Calculated next {day_name} from {from_date} as {result} for chat {chat_id}")
    return result


def _get_this_weekday(from_date, day_name: str, chat_id: str) -> Optional[str]:
    """Get the occurrence of a weekday in the current week (or next if already passed)."""
    day_name_lower = day_name.lower()
    if day_name_lower not in _DAY_MAP:
        logger.warning(f"Unknown day name '{day_name}' for chat {chat_id}")
        return None

    target = _DAY_MAP[day_name_lower]
    days_ahead = target - from_date.weekday()
    if days_ahead < 0:
        days_ahead += 7

    result = (from_date + timedelta(days=days_ahead)).isoformat()
    logger.info(f"Calculated this {day_name} from {from_date} as {result} for chat {chat_id}")
    return result


def _normalize_date(
    date_interpretation: Optional[str],
    mentioned_date_text: Optional[str],
    chat_id: str
) -> Optional[str]:
    """
    Convert date interpretation to YYYY-MM-DD using Asia/Karachi timezone.

    Examples:
        "today" → "2026-03-15"
        "tomorrow" → "2026-03-16"
        "next_monday" → "2026-03-17"
    """
    if not date_interpretation:
        logger.warning(f"No date_interpretation provided for chat {chat_id}")
        return None

    try:
        today = datetime.now(_TZ).date()

        if date_interpretation in ("today", "tonight"):
            result = today.isoformat()
        elif date_interpretation == "tomorrow":
            result = (today + timedelta(days=1)).isoformat()
        elif date_interpretation in ("parso", "day_after_tomorrow"):
            result = (today + timedelta(days=2)).isoformat()
        elif date_interpretation.startswith("next_"):
            result = _get_next_weekday(today, date_interpretation[5:], chat_id)
        elif date_interpretation.startswith("this_"):
            result = _get_this_weekday(today, date_interpretation[5:], chat_id)
        else:
            try:
                result = datetime.fromisoformat(date_interpretation).date().isoformat()
            except ValueError:
                logger.warning(f"Unknown date_interpretation '{date_interpretation}' for chat {chat_id}")
                return None

        logger.info(f"Normalized '{date_interpretation}' to {result} for chat {chat_id}")
        return result

    except Exception as e:
        logger.error(f"Error normalizing date for chat {chat_id}: {e}", exc_info=True)
        return None
