"""
Availability checking tools for the chatbot agent.

This module provides tools for checking court availability and retrieving
available time slots by directly using shared.services.public_service.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, time, datetime, timedelta

from app.agent.tools.sync_bridge import call_sync_service
from shared.services import public_service

logger = logging.getLogger(__name__)


# Time period definitions (24-hour format)
TIME_PERIODS = {
    "morning": ("06:00", "12:00"),
    "afternoon": ("12:00", "18:00"),
    "evening": ("18:00", "21:00"),
    "night": ("21:00", "06:00")  # Crosses midnight
}


def _parse_time(time_str: str) -> Optional[time]:
    """Parse time string to time object. Handles HH:MM and HH:MM:SS formats."""
    if not time_str:
        return None
    
    try:
        # Try HH:MM:SS format first
        if len(time_str) == 8:
            return datetime.strptime(time_str, "%H:%M:%S").time()
        # Try HH:MM format
        elif len(time_str) == 5:
            return datetime.strptime(time_str, "%H:%M").time()
        else:
            logger.warning(f"Invalid time format: {time_str}")
            return None
    except ValueError as e:
        logger.warning(f"Error parsing time '{time_str}': {e}")
        return None


def _normalize_time_display(time_str: str) -> str:
    """
    Normalize time for display, handling :59 cases.
    
    Backend returns slots like "18:00-18:59" but we want to show "6 PM - 7 PM"
    
    Args:
        time_str: Time in HH:MM or HH:MM:SS format
        
    Returns:
        Normalized time string
    """
    if not time_str:
        return time_str
    
    parsed = _parse_time(time_str)
    if not parsed:
        return time_str
    
    # If minutes are 59, round up to next hour for display
    if parsed.minute == 59:
        # Add 1 minute to get to the next hour
        next_hour = (parsed.hour + 1) % 24
        return f"{next_hour:02d}:00"
    
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def _time_to_minutes(t: time) -> int:
    """Convert time to minutes since midnight for comparison."""
    return t.hour * 60 + t.minute


def _categorize_slot_by_period(slot_start_time: str) -> str:
    """
    Categorize a slot into a time period based on its start time.
    
    Args:
        slot_start_time: Start time in HH:MM or HH:MM:SS format
        
    Returns:
        Period name: "morning", "afternoon", "evening", or "night"
    """
    slot_time = _parse_time(slot_start_time)
    if not slot_time:
        return "unknown"
    
    hour = slot_time.hour
    
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 21:
        return "evening"
    else:  # 21-23 or 0-5
        return "night"


def _filter_slots_by_period(slots: List[Dict[str, Any]], period: str) -> List[Dict[str, Any]]:
    """
    Filter slots by time period.
    
    Args:
        slots: List of available slots
        period: Time period name (morning, afternoon, evening, night)
        
    Returns:
        Filtered list of slots
    """
    if not slots or period not in TIME_PERIODS:
        return []
    
    filtered = []
    for slot in slots:
        slot_period = _categorize_slot_by_period(slot.get("start_time", ""))
        if slot_period == period:
            filtered.append(slot)
    
    return filtered


def _filter_slots_by_start_time(slots: List[Dict[str, Any]], start_time: str) -> List[Dict[str, Any]]:
    """
    Filter slots that start at or after the given start time.
    
    Args:
        slots: List of available slots
        start_time: Start time in HH:MM format
        
    Returns:
        Filtered list of slots
    """
    if not slots or not start_time:
        return []
    
    target_start = _parse_time(start_time)
    if not target_start:
        return []
    
    filtered = []
    for slot in slots:
        slot_start = _parse_time(slot.get("start_time", ""))
        if slot_start and slot_start >= target_start:
            filtered.append(slot)
    
    return filtered


def _filter_slots_by_end_time(slots: List[Dict[str, Any]], end_time: str) -> List[Dict[str, Any]]:
    """
    Filter slots that end at or before the given end time.
    
    Args:
        slots: List of available slots
        end_time: End time in HH:MM format
        
    Returns:
        Filtered list of slots
    """
    if not slots or not end_time:
        return []
    
    target_end = _parse_time(end_time)
    if not target_end:
        return []
    
    filtered = []
    for slot in slots:
        slot_end = _parse_time(slot.get("end_time", ""))
        if slot_end and slot_end <= target_end:
            filtered.append(slot)
    
    return filtered


def _filter_slots_by_time_range(
    slots: List[Dict[str, Any]], 
    start_time: str, 
    end_time: str
) -> Dict[str, Any]:
    """
    Filter slots by time range and find matches.
    
    Returns slots that:
    1. Exactly match (single slot with exact start and end)
    2. Cover the range (multiple consecutive slots that together cover the requested time)
    3. Fall within the range (start >= requested start, end <= requested end)
    4. Overlap with the range
    5. Closest alternatives if no matches
    
    Args:
        slots: List of available slots
        start_time: Desired start time (HH:MM format)
        end_time: Desired end time (HH:MM format)
        
    Returns:
        Dictionary with:
        - exact_matches: List of slots that exactly cover the requested range
        - within_range: List of slots within the requested range
        - overlapping: List of slots that overlap
        - closest: List of closest alternatives
        - is_multi_slot_match: Boolean indicating if exact match is from multiple slots
    """
    if not slots or not start_time or not end_time:
        return {
            "exact_matches": [],
            "within_range": [],
            "overlapping": [],
            "closest": [],
            "is_multi_slot_match": False
        }
    
    target_start = _parse_time(start_time)
    target_end = _parse_time(end_time)
    
    if not target_start or not target_end:
        return {
            "exact_matches": [],
            "within_range": [],
            "overlapping": [],
            "closest": [],
            "is_multi_slot_match": False
        }
    
    exact_matches = []
    within_range = []
    overlapping = []
    all_with_distance = []
    
    target_start_min = _time_to_minutes(target_start)
    target_end_min = _time_to_minutes(target_end)
    
    # Handle midnight crossing (e.g., 22:00 to 00:00)
    # If end time is 00:00 (midnight), treat it as 24:00 (1440 minutes)
    if target_end_min == 0 and target_start_min > 0:
        target_end_min = 24 * 60  # 1440 minutes
    elif target_end_min < target_start_min:
        target_end_min += 24 * 60  # Add 24 hours
    
    logger.debug(
        f"Target range: {start_time} ({target_start_min} min) to {end_time} ({target_end_min} min)"
    )
    logger.debug(f"Total slots to check: {len(slots)}")
    
    # First pass: check for single slot matches
    for slot in slots:
        slot_start = _parse_time(slot.get("start_time", ""))
        slot_end = _parse_time(slot.get("end_time", ""))
        
        if not slot_start or not slot_end:
            continue
        
        slot_start_min = _time_to_minutes(slot_start)
        slot_end_min = _time_to_minutes(slot_end)
        
        # Handle :59 case - treat XX:59 as next hour (XX+1:00)
        if slot_end.minute == 59:
            slot_end_min += 1
            # Note: 23:59 + 1 minute = 1440 minutes (midnight)
        
        # Handle midnight crossing for slot (e.g., 23:00 to 00:00)
        elif slot_end_min == 0 and slot_start_min > 0:
            slot_end_min = 24 * 60  # Treat 00:00 as 24:00 (1440 minutes)
        elif slot_end_min < slot_start_min:
            slot_end_min += 24 * 60
        
        logger.debug(
            f"Checking slot: {slot.get('start_time')} ({slot_start_min}) to "
            f"{slot.get('end_time')} ({slot_end_min}) [normalized]"
        )
        
        # Check for exact match (single slot)
        if slot_start_min == target_start_min and slot_end_min == target_end_min:
            exact_matches.append(slot)
            within_range.append(slot)
            overlapping.append(slot)
        # Check if slot is within requested range
        elif slot_start_min >= target_start_min and slot_end_min <= target_end_min:
            within_range.append(slot)
            overlapping.append(slot)
        # Check if slot overlaps with requested range
        elif not (slot_end_min <= target_start_min or slot_start_min >= target_end_min):
            overlapping.append(slot)
        
        # Calculate distance for closest alternatives
        distance = abs(slot_start_min - target_start_min)
        all_with_distance.append((distance, slot))
    
    # Second pass: check if multiple consecutive slots cover the exact range
    if not exact_matches and within_range:
        logger.debug(f"No single exact match found. Checking {len(within_range)} within_range slots for multi-slot match")
        
        # Sort within_range by start time
        sorted_slots = sorted(within_range, key=lambda s: _parse_time(s.get("start_time", "")))
        
        # Check if they form a continuous coverage
        if sorted_slots:
            first_slot_start = _parse_time(sorted_slots[0].get("start_time", ""))
            last_slot_end = _parse_time(sorted_slots[-1].get("end_time", ""))
            
            if first_slot_start and last_slot_end:
                first_start_min = _time_to_minutes(first_slot_start)
                last_end_min = _time_to_minutes(last_slot_end)
                
                # Handle :59 case - treat XX:59 as next hour
                if last_slot_end.minute == 59:
                    last_end_min += 1
                
                # Handle midnight crossing for last slot
                if last_end_min < first_start_min:
                    last_end_min += 24 * 60
                
                logger.debug(
                    f"Multi-slot check: first_start={first_start_min} (target={target_start_min}), "
                    f"last_end={last_end_min} (target={target_end_min})"
                )
                
                # Check if the slots together cover the exact requested range
                if first_start_min == target_start_min and last_end_min == target_end_min:
                    # Verify continuity (no gaps between slots)
                    is_continuous = True
                    for i in range(len(sorted_slots) - 1):
                        current_end = _parse_time(sorted_slots[i].get("end_time", ""))
                        next_start = _parse_time(sorted_slots[i + 1].get("start_time", ""))
                        
                        if current_end and next_start:
                            current_end_min = _time_to_minutes(current_end)
                            # Handle :59 case
                            if current_end.minute == 59:
                                current_end_min += 1
                            next_start_min = _time_to_minutes(next_start)
                            
                            # Handle midnight crossing
                            if next_start_min < current_end_min:
                                next_start_min += 24 * 60
                            
                            gap = abs(next_start_min - current_end_min)
                            logger.debug(f"Gap between slot {i} and {i+1}: {gap} minutes")
                            
                            # Allow 1 minute gap (for :59 to :00 transitions)
                            if gap > 1:
                                is_continuous = False
                                logger.debug(f"Gap too large: {gap} minutes")
                                break
                    
                    if is_continuous:
                        exact_matches = sorted_slots
                        logger.info(
                            f"Found multi-slot exact match: {len(sorted_slots)} consecutive slots "
                            f"cover {start_time} to {end_time}"
                        )
                    else:
                        logger.debug("Slots are not continuous")
    
    # Sort by distance and get top 5 closest
    all_with_distance.sort(key=lambda x: x[0])
    closest = [slot for _, slot in all_with_distance[:5]]
    
    is_multi_slot = len(exact_matches) > 1
    
    return {
        "exact_matches": exact_matches,
        "within_range": within_range,
        "overlapping": overlapping,
        "closest": closest,
        "is_multi_slot_match": is_multi_slot
    }


def _group_slots_by_period(slots: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group slots by time period.
    
    Args:
        slots: List of slots
        
    Returns:
        Dictionary with period names as keys and slot lists as values
    """
    grouped = {
        "morning": [],
        "afternoon": [],
        "evening": [],
        "night": []
    }
    
    for slot in slots:
        period = _categorize_slot_by_period(slot.get("start_time", ""))
        if period in grouped:
            grouped[period].append(slot)
    
    return grouped


async def get_available_slots_tool(
    court_id: int,
    date_val: date,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    time_period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get available time slots for a court on a specific date with flexible filtering.
    
    Logic:
    1. If start_time AND end_time given: Try to match that range, show matches + closest alternatives
    2. If only time_period given: Show slots in that period
    3. If only start_time given: Show slots starting from that time (filtered by period if provided)
    4. If only end_time given: Show slots ending before that time (filtered by period if provided)
    5. If only date given: Show all slots grouped by period
    
    Args:
        court_id: ID of the court
        date_val: Date to check availability for
        start_time: Optional start time (HH:MM format, can be 12 or 24 hour)
        end_time: Optional end time (HH:MM format, can be 12 or 24 hour)
        time_period: Optional time period (morning, afternoon, evening, night)
        
    Returns:
        Dictionary containing availability results with guidance for user
    """
    try:
        logger.info(
            f"Getting available slots: court_id={court_id}, date={date_val}, "
            f"start_time={start_time}, end_time={end_time}, time_period={time_period}"
        )
        
        # Call shared public_service directly using sync bridge
        result = await call_sync_service(
            public_service.get_available_slots,
            db=None,
            court_id=court_id,
            date_val=date_val
        )
        
        # Check if service call succeeded
        if not result.get('success'):
            logger.warning(
                f"Failed to get available slots: {result.get('message')} "
                f"(court_id={court_id}, date={date_val})"
            )
            return {
                "success": False,
                "error": result.get('message', 'Failed to retrieve slots'),
                "date": date_val.isoformat(),
                "court_id": court_id,
                "available_slots": []
            }
        
        # Extract data
        availability_data = result.get('data', {})
        all_slots = availability_data.get('available_slots', [])
        court_name = availability_data.get('court_name', 'Unknown Court')
        
        logger.info(
            f"Retrieved {len(all_slots)} total slots for court_id={court_id} on {date_val}"
        )
        
        # Prepare base response
        response = {
            "success": True,
            "date": date_val.isoformat(),
            "court_id": court_id,
            "court_name": court_name,
            "total_slots": len(all_slots),
            "filter_info": {},
            "user_guidance": ""
        }
        
        # CASE 1: Both start_time and end_time provided
        if start_time and end_time:
            logger.info(f"Case 1: Both start and end time provided: {start_time} to {end_time}")
            
            # Log all slots for debugging
            logger.debug(f"All available slots: {[(s.get('start_time'), s.get('end_time')) for s in all_slots]}")
            
            matches = _filter_slots_by_time_range(all_slots, start_time, end_time)
            
            logger.info(
                f"Time range filter results: exact={len(matches['exact_matches'])}, "
                f"within={len(matches['within_range'])}, overlapping={len(matches['overlapping'])}, "
                f"is_multi_slot={matches.get('is_multi_slot_match', False)}"
            )
            
            # Apply period filter if provided
            if time_period:
                matches["exact_matches"] = _filter_slots_by_period(matches["exact_matches"], time_period)
                matches["within_range"] = _filter_slots_by_period(matches["within_range"], time_period)
                matches["overlapping"] = _filter_slots_by_period(matches["overlapping"], time_period)
                matches["closest"] = _filter_slots_by_period(matches["closest"], time_period)
            
            response["filter_info"] = {
                "type": "time_range",
                "start_time": start_time,
                "end_time": end_time,
                "time_period": time_period
            }
            
            if matches["exact_matches"]:
                response["available_slots"] = matches["exact_matches"]
                response["match_type"] = "exact"
                response["is_multi_slot_match"] = matches.get("is_multi_slot_match", False)
                
                if matches.get("is_multi_slot_match"):
                    response["user_guidance"] = (
                        f"✅ Found {len(matches['exact_matches'])} consecutive slots covering {start_time} to {end_time}. "
                        f"You can also try: different times, morning/afternoon/evening/night slots, or specific dates (YYYY-MM-DD)."
                    )
                else:
                    response["user_guidance"] = (
                        f"✅ Found exact match for {start_time} to {end_time}. "
                        f"You can also try: different times, morning/afternoon/evening/night slots, or specific dates (YYYY-MM-DD)."
                    )
            elif matches["within_range"]:
                response["available_slots"] = matches["within_range"]
                response["match_type"] = "within_range"
                response["user_guidance"] = (
                    f"Found slots within {start_time} to {end_time}. "
                    f"Try: exact times like '6 PM to 7 PM', morning/evening, or different dates."
                )
            elif matches["overlapping"]:
                response["available_slots"] = matches["overlapping"]
                response["match_type"] = "overlapping"
                response["user_guidance"] = (
                    f"Found slots overlapping with {start_time} to {end_time}. "
                    f"Try: adjusting times, morning/afternoon/evening/night, or different dates."
                )
            else:
                response["available_slots"] = matches["closest"]
                response["match_type"] = "closest"
                response["user_guidance"] = (
                    f"No slots available for {start_time} to {end_time}. Showing closest alternatives. "
                    f"Try: morning/afternoon/evening/night, different times, or other dates."
                )
        
        # CASE 2: Only time_period provided
        elif time_period and not start_time and not end_time:
            logger.info(f"Case 2: Only time period provided: {time_period}")
            
            filtered_slots = _filter_slots_by_period(all_slots, time_period)
            
            response["available_slots"] = filtered_slots
            response["filter_info"] = {
                "type": "time_period",
                "time_period": time_period
            }
            response["match_type"] = "period"
            response["user_guidance"] = (
                f"Showing {time_period} slots. "
                f"Try: specific times like '6 to 7 PM', other periods (morning/afternoon/evening/night), or exact dates."
            )
        
        # CASE 3: Only start_time provided
        elif start_time and not end_time:
            logger.info(f"Case 3: Only start time provided: {start_time}")
            
            filtered_slots = _filter_slots_by_start_time(all_slots, start_time)
            
            # Apply period filter if provided
            if time_period:
                filtered_slots = _filter_slots_by_period(filtered_slots, time_period)
            
            response["available_slots"] = filtered_slots
            response["filter_info"] = {
                "type": "start_time_only",
                "start_time": start_time,
                "time_period": time_period
            }
            response["match_type"] = "from_start"
            response["user_guidance"] = (
                f"Showing slots from {start_time} onwards" + 
                (f" in the {time_period}" if time_period else "") + ". "
                f"Try: adding end time like '{start_time} to 8 PM', morning/evening, or different dates."
            )
        
        # CASE 4: Only end_time provided
        elif end_time and not start_time:
            logger.info(f"Case 4: Only end time provided: {end_time}")
            
            filtered_slots = _filter_slots_by_end_time(all_slots, end_time)
            
            # Apply period filter if provided
            if time_period:
                filtered_slots = _filter_slots_by_period(filtered_slots, time_period)
            
            response["available_slots"] = filtered_slots
            response["filter_info"] = {
                "type": "end_time_only",
                "end_time": end_time,
                "time_period": time_period
            }
            response["match_type"] = "until_end"
            response["user_guidance"] = (
                f"Showing slots until {end_time}" +
                (f" in the {time_period}" if time_period else "") + ". "
                f"Try: adding start time like '6 PM to {end_time}', morning/evening, or different dates."
            )
        
        # CASE 5: Only date provided (no time filters)
        else:
            logger.info(f"Case 5: Only date provided, showing all slots")
            
            # Group by period for better display
            grouped = _group_slots_by_period(all_slots)
            
            response["available_slots"] = all_slots
            response["slots_by_period"] = grouped
            response["filter_info"] = {
                "type": "full_day"
            }
            response["match_type"] = "all"
            response["user_guidance"] = (
                f"Showing all available slots. "
                f"Try: specific times like '6 to 7 PM', morning/afternoon/evening/night, or exact dates (YYYY-MM-DD)."
            )
        
        logger.info(
            f"Availability check complete: found {len(response.get('available_slots', []))} slots, "
            f"match_type={response.get('match_type')}"
        )
        
        return response
            
    except Exception as e:
        logger.error(f"Error getting available slots: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "date": date_val.isoformat() if date_val else None,
            "court_id": court_id,
            "available_slots": []
        }


# Tool registry for easy access
AVAILABILITY_TOOLS = {
    "get_available_slots": get_available_slots_tool,
}
