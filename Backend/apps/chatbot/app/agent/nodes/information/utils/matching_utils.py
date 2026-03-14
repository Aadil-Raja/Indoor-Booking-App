"""
Matching utilities for property and court resolution.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Sport name synonyms/aliases for flexible matching
SPORT_SYNONYMS = {
    "football": ["futsal", "soccer"],
    "soccer": ["futsal", "football"],
    "futsal": ["football", "soccer"],
    "badminton": ["shuttle", "shuttlecock"],
    "table tennis": ["ping pong", "tt"],
    "ping pong": ["table tennis", "tt"],
    "basketball": ["basket", "hoops"],
    "tennis": ["lawn tennis"],
    "cricket": ["indoor cricket"],
}


def _normalize_sport_name(name: str) -> str:
    """Normalize sport name for matching (lowercase, strip)."""
    return name.lower().strip()


def _get_sport_aliases(sport_name: str) -> List[str]:
    """Get all aliases for a sport name including the original."""
    normalized = _normalize_sport_name(sport_name)
    aliases = [normalized]
    if normalized in SPORT_SYNONYMS:
        aliases.extend(SPORT_SYNONYMS[normalized])
    return aliases


def _filter_courts_by_property(
    courts: List[Dict],
    property_id: Optional[int]
) -> List[Dict]:
    if not property_id:
        return courts
    return [c for c in courts if c.get("property_id") == property_id]


def _match_property(
    property_name: str,
    available_properties: List[Dict],
    chat_id: str
) -> Optional[Dict]:
    """
    Match property by name with fuzzy matching.

    Priority:
    1. Exact name match
    2. Starts-with match
    3. Contains match (partial)
    4. Description match (fallback)
    """
    name_lower = _normalize_sport_name(property_name)

    for prop in available_properties:
        if _normalize_sport_name(prop.get("name") or "") == name_lower:
            logger.debug(f"Exact property match: '{property_name}' → {prop.get('id')}")
            return prop

    for prop in available_properties:
        if _normalize_sport_name(prop.get("name") or "").startswith(name_lower):
            logger.debug(f"Starts-with property match: '{property_name}' → {prop.get('id')}")
            return prop

    for prop in available_properties:
        pname = _normalize_sport_name(prop.get("name") or "")
        if name_lower in pname or pname in name_lower:
            logger.debug(f"Partial property match: '{property_name}' → {prop.get('id')}")
            return prop

    for prop in available_properties:
        description = _normalize_sport_name(prop.get("description") or "")
        if description and name_lower in description:
            logger.debug(f"Description property match: '{property_name}' → {prop.get('id')}")
            return prop

    logger.warning(f"No property match for '{property_name}' chat {chat_id}")
    return None


def _match_court(
    court_name: str,
    available_courts: List[Dict],
    property_id: Optional[int],
    chat_id: str
) -> tuple[Optional[str], List[int]]:
    """
    Match court by sport_type, name, or description with fuzzy matching.

    Returns tuple: (sport_type, [court_ids])

    Priority:
    1. Exact sport_type match in sport_types array
    2. Synonym sport_type match (football → futsal)
    3. Exact name match
    4. Partial sport_type match (contains)
    5. Partial name match (contains)
    6. Description match (contains)
    """
    name_lower = _normalize_sport_name(court_name)
    user_aliases = _get_sport_aliases(court_name)
    filtered = _filter_courts_by_property(available_courts, property_id)

    # Level 1: Exact sport_type match
    for court in filtered:
        for sport_type in court.get("sport_types", []):
            if _normalize_sport_name(sport_type) == name_lower:
                logger.debug(f"Exact sport_type match: '{court_name}' → {sport_type}")
                matching_ids = [c["id"] for c in filtered if sport_type in c.get("sport_types", [])]
                return sport_type, matching_ids

    # Level 2: Synonym sport_type match
    for court in filtered:
        for sport_type in court.get("sport_types", []):
            if any(alias in _get_sport_aliases(sport_type) for alias in user_aliases):
                logger.debug(f"Synonym sport_type match: '{court_name}' → {sport_type}")
                matching_ids = [c["id"] for c in filtered if sport_type in c.get("sport_types", [])]
                return sport_type, matching_ids

    # Level 3: Exact name match
    for court in filtered:
        if _normalize_sport_name(court.get("name") or "") == name_lower:
            logger.debug(f"Exact name match: '{court_name}' → {court.get('id')}")
            sport_types = court.get("sport_types", [])
            return (sport_types[0] if sport_types else court.get("name")), [court["id"]]

    # Level 4: Partial sport_type match
    for court in filtered:
        for sport_type in court.get("sport_types", []):
            st_lower = _normalize_sport_name(sport_type)
            if name_lower in st_lower or st_lower in name_lower:
                logger.debug(f"Partial sport_type match: '{court_name}' → {sport_type}")
                matching_ids = [c["id"] for c in filtered if sport_type in c.get("sport_types", [])]
                return sport_type, matching_ids

    # Level 5: Partial name match
    for court in filtered:
        cname = _normalize_sport_name(court.get("name") or "")
        if name_lower in cname or cname in name_lower:
            logger.debug(f"Partial name match: '{court_name}' → {court.get('id')}")
            sport_types = court.get("sport_types", [])
            return (sport_types[0] if sport_types else court.get("name")), [court["id"]]

    # Level 6: Description match
    for court in filtered:
        description = _normalize_sport_name(court.get("description") or "")
        if description and name_lower in description:
            logger.debug(f"Description match: '{court_name}' → {court.get('id')}")
            sport_types = court.get("sport_types", [])
            return (sport_types[0] if sport_types else court.get("name")), [court["id"]]

    logger.warning(f"No court match for '{court_name}' chat {chat_id}")
    return None, []


def _resolve_property_selection(
    mentioned_name: Optional[str],
    available_properties: List[Dict],
    chat_id: str
) -> Optional[Dict]:
    if not mentioned_name or not available_properties:
        return None
    try:
        index = int(mentioned_name) - 1
        if 0 <= index < len(available_properties):
            return available_properties[index]
    except (ValueError, TypeError):
        pass
    return _match_property(mentioned_name, available_properties, chat_id)


def _resolve_court_selection(
    mentioned_name: Optional[str],
    available_courts: List[Dict],
    property_id: Optional[int],
    chat_id: str
) -> tuple[Optional[str], List[int]]:
    """
    Resolve court selection to sport type and matching court IDs.
    Returns: (sport_type, [court_ids]) or (None, [])
    """
    if not mentioned_name or not available_courts:
        return None, []

    filtered = _filter_courts_by_property(available_courts, property_id)

    try:
        index = int(mentioned_name) - 1
        unique_sport_types = []
        for court in filtered:
            for st in court.get("sport_types", []):
                if st not in unique_sport_types:
                    unique_sport_types.append(st)

        if 0 <= index < len(unique_sport_types):
            selected_sport = unique_sport_types[index]
            matching_ids = [c["id"] for c in filtered if selected_sport in c.get("sport_types", [])]
            return selected_sport, matching_ids
    except (ValueError, TypeError):
        pass

    return _match_court(mentioned_name, available_courts, property_id, chat_id)
