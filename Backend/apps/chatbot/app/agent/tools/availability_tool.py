"""
Availability checking tools for the chatbot agent.

This module provides tools for checking court availability and retrieving
available time slots by directly using shared.services.public_service.

Period definitions (Rule 1):
    morning   : 04:00 – 11:59
    afternoon : 12:00 – 16:59
    evening   : 17:00 – 20:59
    night     : 21:00 – 03:59  (00:00–03:59 belongs to the NEXT calendar day)

Time-correction rules (Rules 2–4 & 8):
    - Boundary hours at period transitions are allowed (Rule 2).
    - If time already fits the period, keep it (Rule 3).
    - If hour < 12 and period expects PM, add 12 (Rule 4).
    - If correction still doesn't fit → reject, don't over-guess (Rule 8).

Night rollover rule (Rule 5):
    - 21:00–23:59  → selected date
    - 00:00–03:59  → next calendar day

Today rule (Rule 7):
    - Reject slots whose start_datetime <= now  (Asia/Karachi timezone).
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, time, datetime, timedelta

from app.agent.tools.sync_bridge import call_sync_service
from shared.services import public_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Period definitions  (Rule 1)
# ---------------------------------------------------------------------------
# Each entry: (start_hour_inclusive, end_hour_inclusive)
# Night is represented as two ranges because it crosses midnight.
PERIOD_RANGES: Dict[str, Any] = {
    "morning":   (4,  11),
    "afternoon": (12, 16),
    "evening":   (17, 20),
    "night":     [(21, 23), (0, 3)],   # 00:00–03:59 = next day segment
}

# Periods that require PM correction (hour + 12) when hour < 12
_PM_PERIODS = {"afternoon", "evening", "night"}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _parse_time(time_str: str) -> Optional[time]:
    """Parse HH:MM or HH:MM:SS string → time object."""
    if not time_str:
        return None
    try:
        if len(time_str) == 8:
            return datetime.strptime(time_str, "%H:%M:%S").time()
        if len(time_str) == 5:
            return datetime.strptime(time_str, "%H:%M").time()
        logger.warning(f"Invalid time format: {time_str}")
        return None
    except ValueError as e:
        logger.warning(f"Error parsing time '{time_str}': {e}")
        return None


def _time_to_minutes(t: time) -> int:
    """Convert time → minutes since midnight."""
    return t.hour * 60 + t.minute


def _fmt_hhmm(hour: int, minute: int) -> str:
    """Format hour/minute back to HH:MM, handling 24-hour wrap."""
    hour = hour % 24
    return f"{hour:02d}:{minute:02d}"


# ---------------------------------------------------------------------------
# Rule 1 – period membership check
# ---------------------------------------------------------------------------

def _is_time_valid_for_period(hour: int, period: str) -> bool:
    """Return True if *hour* falls inside the allowed range for *period*."""
    ranges = PERIOD_RANGES.get(period)
    if ranges is None:
        return False
    if period == "night":
        return any(lo <= hour <= hi for lo, hi in ranges)
    lo, hi = ranges
    return lo <= hour <= hi


# ---------------------------------------------------------------------------
# Rule 2 – boundary hours
# ---------------------------------------------------------------------------
# Each period allows its neighbour's boundary hour at the transition point:
#
#   morning   : 04:00–11:59  → also allows 12:00 as upper boundary
#   afternoon : 12:00–16:59  → also allows 17:00 as upper boundary
#   evening   : 17:00–20:59  → also allows 21:00 as upper boundary
#   night     : 21:00–03:59  → also allows 04:00 as upper boundary
#
# Example from spec: "10–12 morning → 10:00–12:00"  (12 is safe upper bound)
#                    "11–12 morning → valid"
#                    "4 morning     → valid start"
#                    "9 night       → start of night"  (corrected to 21:00)

# Map period → extra boundary hours allowed beyond the strict range
_PERIOD_BOUNDARY_HOURS: Dict[str, set] = {
    "morning":   {12},   # 12:00 is the upper boundary (start of afternoon)
    "afternoon": {17},   # 17:00 is the upper boundary (start of evening)
    "evening":   {21},   # 21:00 is the upper boundary (start of night)
    "night":     {4},    # 04:00 is the upper boundary (start of morning next day)
}


def _is_time_valid_for_period_with_boundary(hour: int, period: str) -> bool:
    """
    Rule 1 + Rule 2: return True if hour is inside the period's range
    OR is the allowed upper boundary hour for that period.
    """
    if _is_time_valid_for_period(hour, period):
        return True
    return hour in _PERIOD_BOUNDARY_HOURS.get(period, set())


# ---------------------------------------------------------------------------
# Rule 3 – keep if already valid
# Rule 4 – simple 12-hour correction
# Rule 8 – reject if still doesn't fit
# ---------------------------------------------------------------------------

def _correct_time_for_period(time_str: str, period: str) -> Optional[str]:
    """
    Try to return a corrected time string that fits *period*.

    Rules applied in order:
      3. If already valid → return as-is.
      4. If hour < 12 and period is a PM period → add 12.
         Special sub-case: 12 night → 00 (midnight, next-day segment).
      8. If still doesn't fit → return None (caller should reject).
    """
    parsed = _parse_time(time_str)
    if not parsed or period not in PERIOD_RANGES:
        return None

    hour = parsed.hour
    minute = parsed.minute

    # Rule 3 – already valid (includes boundary hours per Rule 2)
    if _is_time_valid_for_period_with_boundary(hour, period):
        return time_str

    # Rule 4 special sub-case: "12 night" means midnight (00:00)
    if hour == 12 and period == "night":
        corrected = _fmt_hhmm(0, minute)
        logger.info(f"Rule-4 special: {time_str} night → {corrected} (midnight)")
        return corrected

    # Rule 4 – add 12 when hour < 12 and period expects PM
    if hour < 12 and period in _PM_PERIODS:
        corrected_hour = hour + 12
        corrected = _fmt_hhmm(corrected_hour, minute)
        # Verify the corrected value actually fits (Rule 8 guard)
        if _is_time_valid_for_period_with_boundary(corrected_hour % 24, period):
            logger.info(f"Rule-4 correction: {time_str} {period} → {corrected}")
            return corrected

    # Rule 8 – don't over-guess, reject
    logger.info(f"Rule-8 reject: {time_str} does not fit period '{period}' after correction attempt")
    return None


# ---------------------------------------------------------------------------
# Rule 5 – night rollover: split start/end across calendar dates
# ---------------------------------------------------------------------------

def _resolve_night_dates(
    selected_date: date,
    start_time_str: str,
    end_time_str: str,
) -> Tuple[date, date]:
    """
    Given a selected date and a night booking's start/end times, return
    (start_date, end_date) according to the night rollover rule:
        21:00–23:59  → selected_date
        00:00–03:59  → selected_date + 1 day
    """
    start = _parse_time(start_time_str)
    end = _parse_time(end_time_str)

    start_date = selected_date
    end_date = selected_date

    if start and 0 <= start.hour <= 3:
        start_date = selected_date + timedelta(days=1)
    if end and 0 <= end.hour <= 3:
        end_date = selected_date + timedelta(days=1)
    # end == 0:00 (midnight boundary) also belongs to next day
    if end and end.hour == 0 and end.minute == 0:
        end_date = selected_date + timedelta(days=1)

    return start_date, end_date


def _adjust_date_for_overnight_booking(
    date_val: date,
    start_time: Optional[str],
    end_time: Optional[str],
    period: Optional[str],
) -> Tuple[date, Optional[str], Optional[str]]:
    """
    Apply the night rollover rule (Rule 5) to adjust the query date used
    when fetching slots from the backend.

    Logic:
    - If both start and end are in the early-morning segment (00:00–03:59),
      the entire booking is on the *next* calendar day → query next day.
    - If start is in late-night (21:00+) and end is in early-morning (00:00–03:59),
      the booking spans midnight but starts on selected_date → query selected_date.
    - Otherwise keep selected_date.
    """
    if not start_time or not end_time:
        return date_val, start_time, end_time

    parsed_start = _parse_time(start_time)
    parsed_end = _parse_time(end_time)

    if not parsed_start or not parsed_end:
        return date_val, start_time, end_time

    sh = parsed_start.hour
    eh = parsed_end.hour

    # Both times in early morning → next-day booking
    if 0 <= sh <= 3 and 0 <= eh <= 3:
        logger.info(f"Night rollover: both times early-morning, shifting date {date_val} → next day")
        return date_val + timedelta(days=1), start_time, end_time

    # Overnight span (starts late night, ends early morning) → keep selected date
    if sh >= 21 and 0 <= eh <= 3:
        logger.info(f"Night rollover: overnight span {start_time}–{end_time}, keeping date {date_val}")
        return date_val, start_time, end_time

    return date_val, start_time, end_time


# ---------------------------------------------------------------------------
# Slot normalisation  (backend returns XX:59, we normalise to (XX+1):00)
# ---------------------------------------------------------------------------

def _normalize_slot(slot: Dict[str, Any]) -> Dict[str, Any]:
    """Convert end_time XX:59 → (XX+1):00 for consistent matching."""
    normalized = slot.copy()
    end_str = slot.get("end_time", "")
    if end_str:
        parsed_end = _parse_time(end_str)
        if parsed_end and parsed_end.minute == 59:
            next_hour = (parsed_end.hour + 1) % 24
            fmt = "%H:%M:%S" if len(end_str) == 8 else "%H:%M"
            normalized["end_time"] = (
                f"{next_hour:02d}:00:00" if fmt == "%H:%M:%S" else f"{next_hour:02d}:00"
            )
            normalized["end_time_normalized"] = True
    return normalized


def _normalize_all_slots(slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_normalize_slot(s) for s in slots]


# ---------------------------------------------------------------------------
# Time-period validation wrapper
# ---------------------------------------------------------------------------

def _validate_time_period_consistency(
    start_time: Optional[str],
    end_time: Optional[str],
    period: Optional[str],
) -> Dict[str, Any]:
    """
    Validate start_time and end_time against period, applying corrections
    (Rules 2–4, 8).  Returns a result dict with keys:
        valid, corrected_start_time, corrected_end_time, error
    """
    result: Dict[str, Any] = {
        "valid": True,
        "corrected_start_time": start_time,
        "corrected_end_time": end_time,
        "error": None,
    }

    if not period:
        return result

    if start_time:
        corrected = _correct_time_for_period(start_time, period)
        if corrected is None:
            result["valid"] = False
            result["error"] = (
                f"Start time {start_time} doesn't fit the '{period}' period "
                f"and could not be corrected. Please use a time appropriate for {period}."
            )
            return result
        result["corrected_start_time"] = corrected

    if end_time:
        corrected = _correct_time_for_period(end_time, period)
        if corrected is None:
            result["valid"] = False
            result["error"] = (
                f"End time {end_time} doesn't fit the '{period}' period "
                f"and could not be corrected. Please use a time appropriate for {period}."
            )
            return result
        result["corrected_end_time"] = corrected

    return result


# ---------------------------------------------------------------------------
# Period categorisation (for grouping/filtering slots)
# ---------------------------------------------------------------------------

def _categorize_slot_by_period(slot_start_time: str) -> str:
    """Return the period name for a slot's start time."""
    t = _parse_time(slot_start_time)
    if not t:
        return "unknown"
    h = t.hour
    if 4 <= h <= 11:
        return "morning"
    if 12 <= h <= 16:
        return "afternoon"
    if 17 <= h <= 20:
        return "evening"
    # 21-23 and 0-3
    return "night"


# ---------------------------------------------------------------------------
# Slot filtering by time range  (with multi-slot midnight-crossing fix)
# ---------------------------------------------------------------------------

def _filter_slots_by_time_range(
    slots: List[Dict[str, Any]],
    start_time: str,
    end_time: str,
) -> Dict[str, Any]:
    """
    Filter *slots* by the requested [start_time, end_time] range.

    Priority:
      1. Exact single-slot match
      2. Exact multi-slot match (consecutive slots that together cover the range)
      3. Partial matches (slots overlapping the range)
      4. Nearby alternatives (within 2 hours of requested start)
      5. All slots (when total < 10)

    Midnight crossing is handled throughout by converting times to
    "minutes since midnight" and adding 24*60 when a wrap is detected.
    """
    empty = {
        "exact_matches": [],
        "partial_matches": [],
        "nearby_alternatives": [],
        "all_slots": [],
        "is_multi_slot_match": False,
    }

    if not slots or not start_time or not end_time:
        return empty

    normalized_slots = _normalize_all_slots(slots)

    target_start = _parse_time(start_time)
    target_end = _parse_time(end_time)
    if not target_start or not target_end:
        return empty

    target_start_min = _time_to_minutes(target_start)
    target_end_min = _time_to_minutes(target_end)

    # Handle midnight crossing for target range
    if target_end_min <= target_start_min:
        target_end_min += 24 * 60   # e.g. 22:00 → 00:00 becomes 22:00 → 24:00

    exact_matches: List[Dict] = []
    inner_slots: List[Dict] = []   # slots completely inside the range (multi-slot candidates)
    partial_matches: List[Dict] = []
    nearby_alternatives: List[Dict] = []

    for slot in normalized_slots:
        slot_start = _parse_time(slot.get("start_time", ""))
        slot_end = _parse_time(slot.get("end_time", ""))
        if not slot_start or not slot_end:
            continue

        s_min = _time_to_minutes(slot_start)
        e_min = _time_to_minutes(slot_end)

        # Lift slot into the same "timeline" as target if it crosses midnight
        if e_min <= s_min:
            e_min += 24 * 60
        # If slot starts before target but would actually be "after midnight"
        # in relation to the target range, lift it
        if s_min < target_start_min and (s_min + 24 * 60) <= target_end_min:
            s_min += 24 * 60
            e_min += 24 * 60

        # Single-slot exact match
        if s_min == target_start_min and e_min == target_end_min:
            exact_matches.append(slot)
            continue

        # Completely inside the requested range → multi-slot candidate
        if s_min >= target_start_min and e_min <= target_end_min:
            inner_slots.append(slot)
            continue

        # Overlaps (partial)
        if s_min < target_end_min and e_min > target_start_min:
            partial_matches.append(slot)
            continue

        # Nearby (within 2 hours of requested start)
        if abs(s_min - target_start_min) <= 120:
            nearby_alternatives.append(slot)

    # ---- Multi-slot exact match (uses inner_slots) -------------------------
    if not exact_matches and inner_slots:
        # Sort inner slots by start time (in the lifted timeline)
        def _slot_start_min(s: Dict) -> int:
            t = _parse_time(s.get("start_time", ""))
            if not t:
                return 0
            m = _time_to_minutes(t)
            # lift if needed
            if m < target_start_min and (m + 24 * 60) <= target_end_min:
                m += 24 * 60
            return m

        sorted_inner = sorted(inner_slots, key=_slot_start_min)

        # Try to build a consecutive sequence from target_start_min to target_end_min
        sequence: List[Dict] = []
        current_end = target_start_min

        for slot in sorted_inner:
            t = _parse_time(slot.get("start_time", ""))
            te = _parse_time(slot.get("end_time", ""))
            if not t or not te:
                break
            s_min = _slot_start_min(slot)
            e_min = _time_to_minutes(te)
            if e_min <= _time_to_minutes(t):
                e_min += 24 * 60
            if s_min >= target_start_min and (e_min - s_min + s_min) > target_start_min:
                # re-lift e_min relative to our timeline
                if e_min < s_min:
                    e_min += 24 * 60
            # align e_min to lifted s_min
            if s_min >= 24 * 60:
                if e_min < s_min:
                    e_min += 24 * 60

            if s_min == current_end:
                sequence.append(slot)
                current_end = e_min
                if current_end == target_end_min:
                    exact_matches = sequence
                    break
            else:
                # Gap found – reset
                sequence = []
                current_end = target_start_min

    # Sort nearby by distance
    nearby_alternatives.sort(
        key=lambda s: abs(
            _time_to_minutes(_parse_time(s.get("start_time", ""))) - target_start_min
        )
        if _parse_time(s.get("start_time", ""))
        else 9999
    )
    nearby_alternatives = nearby_alternatives[:5]

    all_slots_fallback = normalized_slots if len(normalized_slots) < 10 else []

    return {
        "exact_matches": exact_matches,
        "partial_matches": partial_matches,
        "nearby_alternatives": nearby_alternatives,
        "all_slots": all_slots_fallback,
        "is_multi_slot_match": len(exact_matches) > 1,
    }


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

async def get_available_slots_tool(
    court_id: int,
    date_val: date,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    time_period: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get available time slots for a court on a specific date with flexible filtering.

    Logic:
      1. If start_time AND end_time given → match that range, show exact / partial / nearby.
      2. If only time_period given → show slots in that period.
      3. If only date given → show all slots grouped by period.

    Applies all period/time correction rules (Rules 1–5, 7, 8) before querying.

    Args:
        court_id    : ID of the court.
        date_val    : Date to check (Asia/Karachi).
        start_time  : Optional start time (HH:MM).
        end_time    : Optional end time (HH:MM).
        time_period : Optional period name (morning / afternoon / evening / night).

    Returns:
        Dict with availability results.
    """
    try:
        logger.info(
            f"get_available_slots_tool: court_id={court_id}, date={date_val}, "
            f"start={start_time}, end={end_time}, period={time_period}"
        )

        # ------------------------------------------------------------------ #
        # Step 1 – validate / correct times against period (Rules 2–4, 8)    #
        # ------------------------------------------------------------------ #
        # Key rule: explicit start_time + end_time always take precedence.
        # If a stale/conflicting time_period was carried from session state
        # but the times don't fit it, DROP the period and infer the correct
        # one from the actual times rather than returning an error.
        if time_period and (start_time or end_time):
            validation = _validate_time_period_consistency(start_time, end_time, time_period)
            if not validation["valid"]:
                # Times are explicit and authoritative — infer period from them
                inferred_period = _categorize_slot_by_period(start_time) if start_time else None
                logger.warning(
                    f"Period '{time_period}' conflicts with explicit times "
                    f"{start_time}-{end_time}. "
                    f"Dropping stale period, inferred as '{inferred_period}'. "
                    f"Original error: {validation['error']}"
                )
                time_period = inferred_period  # use inferred (or None) going forward
            else:
                if validation["corrected_start_time"] != start_time:
                    logger.info(f"Corrected start_time: {start_time} -> {validation['corrected_start_time']}")
                    start_time = validation["corrected_start_time"]
                if validation["corrected_end_time"] != end_time:
                    logger.info(f"Corrected end_time: {end_time} -> {validation['corrected_end_time']}")
                    end_time = validation["corrected_end_time"]

        # ------------------------------------------------------------------ #
        # Step 2 – apply night rollover rule (Rule 5)                        #
        # ------------------------------------------------------------------ #
        original_date = date_val
        date_val, start_time, end_time = _adjust_date_for_overnight_booking(
            date_val, start_time, end_time, time_period
        )
        if date_val != original_date:
            logger.info(f"Night rollover: date shifted {original_date} → {date_val}")

        # ------------------------------------------------------------------ #
        # Step 3 – Rule 7: reject past dates / past times (Asia/Karachi)     #
        # ------------------------------------------------------------------ #
        now = datetime.now()          # assumes server runs in Asia/Karachi
        current_date = now.date()
        current_time = now.time()

        if date_val < current_date:
            return {
                "success": False,
                "error": (
                    f"Cannot check availability for past date {date_val.isoformat()}. "
                    "Please select today or a future date."
                ),
                "date": date_val.isoformat(),
                "court_id": court_id,
                "available_slots": [],
                "is_past_date": True,
            }

        is_today = date_val == current_date
        if is_today and start_time:
            requested_start = _parse_time(start_time)
            if requested_start and requested_start <= current_time:
                return {
                    "success": False,
                    "error": (
                        f"The requested time {start_time} has already passed today. "
                        "Please select an upcoming time slot."
                    ),
                    "date": date_val.isoformat(),
                    "court_id": court_id,
                    "available_slots": [],
                    "is_past_time": True,
                    "current_time": current_time.strftime("%H:%M"),
                }

        # ------------------------------------------------------------------ #
        # Step 4 – fetch slots from backend                                   #
        # ------------------------------------------------------------------ #
        result = await call_sync_service(
            public_service.get_available_slots,
            db=None,
            court_id=court_id,
            date_val=date_val,
        )

        if not result.get("success"):
            logger.warning(f"Backend error: {result.get('message')}")
            return {
                "success": False,
                "error": result.get("message", "Failed to retrieve slots"),
                "date": date_val.isoformat(),
                "court_id": court_id,
                "available_slots": [],
            }

        availability_data = result.get("data", {})
        all_slots: List[Dict] = availability_data.get("available_slots", [])
        court_name: str = availability_data.get("court_name", "Unknown Court")

        logger.info(f"Backend returned {len(all_slots)} slots for court {court_id} on {date_val}")

        # Normalise XX:59 → (XX+1):00
        all_slots = _normalize_all_slots(all_slots)

        # ------------------------------------------------------------------ #
        # Step 5 – Rule 7: strip past slots when checking today              #
        # ------------------------------------------------------------------ #
        if is_today:
            before = len(all_slots)
            all_slots = [
                s for s in all_slots
                if (t := _parse_time(s.get("start_time", ""))) and t > current_time
            ]
            logger.info(f"Stripped {before - len(all_slots)} past slots for today")

            if not all_slots:
                return {
                    "success": False,
                    "error": (
                        "No upcoming slots available for today. "
                        "All time slots have passed. Please try tomorrow or a future date."
                    ),
                    "date": date_val.isoformat(),
                    "court_id": court_id,
                    "court_name": court_name,
                    "available_slots": [],
                    "is_today": True,
                    "current_time": current_time.strftime("%H:%M"),
                }

        # ------------------------------------------------------------------ #
        # Step 6 – build response                                             #
        # ------------------------------------------------------------------ #
        response: Dict[str, Any] = {
            "success": True,
            "date": date_val.isoformat(),
            "court_id": court_id,
            "court_name": court_name,
            "total_slots": len(all_slots),
        }

        # Case 1: explicit time range
        if start_time and end_time:
            logger.info(f"Filtering by range: {start_time} – {end_time}")
            matches = _filter_slots_by_time_range(all_slots, start_time, end_time)

            if matches["exact_matches"]:
                response["available_slots"] = matches["exact_matches"]
                response["match_type"] = "exact"
                response["is_multi_slot_match"] = matches["is_multi_slot_match"]
                logger.info(f"Exact match: {len(matches['exact_matches'])} slot(s)")

            elif matches["partial_matches"]:
                response["available_slots"] = matches["partial_matches"]
                response["match_type"] = "partial"
                response["message"] = (
                    f"Exact time {start_time}–{end_time} not available. "
                    "Showing slots that partially overlap with your requested time."
                )

            elif matches["nearby_alternatives"]:
                response["available_slots"] = matches["nearby_alternatives"]
                response["match_type"] = "nearby"
                response["message"] = (
                    f"No slots available for {start_time}–{end_time}. "
                    "Showing nearby time slots."
                )

            elif matches["all_slots"]:
                response["available_slots"] = matches["all_slots"]
                response["match_type"] = "all"
                response["message"] = (
                    f"No slots available for {start_time}–{end_time}. "
                    "Showing all available slots for this date."
                )

            else:
                response["available_slots"] = []
                response["match_type"] = "none"
                response["message"] = (
                    f"No slots available for {start_time}–{end_time} or nearby times."
                )

        # Case 2: period only
        elif time_period:
            logger.info(f"Filtering by period: {time_period}")
            response["available_slots"] = [
                s for s in all_slots
                if _categorize_slot_by_period(s.get("start_time", "")) == time_period
            ]
            response["match_type"] = "period"

        # Case 3: date only → all slots
        else:
            response["available_slots"] = all_slots
            response["match_type"] = "all"

        logger.info(f"Returning {len(response.get('available_slots', []))} slots")
        return response

    except Exception as exc:
        logger.error(f"Unexpected error in get_available_slots_tool: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "date": date_val.isoformat() if date_val else None,
            "court_id": court_id,
            "available_slots": [],
        }


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
AVAILABILITY_TOOLS = {
    "get_available_slots": get_available_slots_tool,
}