from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.repositories import media_repo
from shared.repositories import property_repo, court_repo, pricing_repo, availability_repo
from shared.services import public_service
from shared.utils.response_utils import make_response
from shared.models import Property, Court, CourtPricing, Booking, BookingStatus
from datetime import date, time, datetime, timedelta
from typing import Optional

# Re-export public_service functions for backward compatibility
search_properties = public_service.search_properties
get_property_details = public_service.get_property_details
get_court_details = public_service.get_court_details
get_court_pricing_for_date = public_service.get_court_pricing_for_date
get_available_slots = public_service.get_available_slots

