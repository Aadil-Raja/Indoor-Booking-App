from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.deps.db import get_db
from shared.services import public_service
from typing import Optional
from datetime import date

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/courts")
def search_courts(
    search: Optional[str] = Query(None, description="Search by court name, property name, address, or city"),
    date: Optional[str] = Query(None, description="Date for availability check (YYYY-MM-DD)"),
    start_time: Optional[str] = Query(None, description="Start time for availability check (HH:MM)"),
    sport_type: Optional[str] = Query(None, description="Filter by sport type"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price per hour"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price per hour"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Search courts with multiple filters (Public endpoint)
    
    Filters:
    - search: Search in court name, property name, address, or city
    - date: Check availability for specific date (YYYY-MM-DD)
    - start_time: Check availability for specific time (HH:MM, requires date)
    - sport_type: Filter by sport type (futsal, padel, cricket, etc.)
    - min_price/max_price: Filter by price range
    - page/limit: Pagination
    
    Returns:
    - Courts with property info, media, base price
    - If date+time provided, includes availability status
    """
    return public_service.search_courts(
        db,
        search=search,
        date=date,
        start_time=start_time,
        sport_type=sport_type,
        min_price=min_price,
        max_price=max_price,
        page=page,
        limit=limit
    )


@router.get("/properties")
def search_properties(
    city: Optional[str] = Query(None, description="Filter by city"),
    sport_type: Optional[str] = Query(None, description="Filter by sport type"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price per hour"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price per hour"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Search and filter properties (Public endpoint)
    
    Filters:
    - city: Filter by city name
    - sport_type: Filter by sport type (futsal, padel, cricket, etc.)
    - min_price/max_price: Filter by price range
    - page/limit: Pagination
    """
    return public_service.search_properties(
        db,
        city=city,
        sport_type=sport_type,
        min_price=min_price,
        max_price=max_price,
        page=page,
        limit=limit
    )


@router.get("/properties/{property_id}")
def get_property_details(
    property_id: int,
    db: Session = Depends(get_db)
):
    """Get property details with courts and media (Public endpoint)"""
    return public_service.get_property_details(db, property_id=property_id)


@router.get("/courts/{court_id}")
def get_court_details(
    court_id: int,
    db: Session = Depends(get_db)
):
    """Get court details with pricing and media (Public endpoint)"""
    return public_service.get_court_details(db, court_id=court_id)


@router.get("/courts/{court_id}/pricing")
def get_court_pricing_for_date(
    court_id: int,
    date: date = Query(..., description="Date to check pricing (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Get pricing for a specific court and date (Public endpoint)"""
    return public_service.get_court_pricing_for_date(db, court_id=court_id, date_val=date)


@router.get("/courts/{court_id}/available-slots")
def get_available_slots(
    court_id: int,
    date: date = Query(..., description="Date to check availability (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get available time slots for a court on a specific date (Public endpoint)
    
    Returns slots that are:
    - Not blocked by owner
    - Not already booked
    - Within court's pricing hours
    """
    return public_service.get_available_slots(db, court_id=court_id, date_val=date)



@router.get("/courts/{court_id}/availability")
def get_court_availability(
    court_id: int,
    date: date = Query(..., description="Date to check availability (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Alias endpoint for getting available slots (matches frontend expectation)
    
    Returns slots that are:
    - Not blocked by owner
    - Not already booked
    - Within court's pricing hours
    """
    return public_service.get_available_slots(db, court_id=court_id, date_val=date)
