"""
Unit tests for flow validation utilities.

This module tests the flow validation functions that ensure sequential ordering
and context-aware step skipping in the booking flow.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import pytest
from app.agent.nodes.booking.flow_validation import (
    get_next_incomplete_step,
    validate_booking_flow_sequence,
    should_skip_to_next_step,
    validate_required_fields_for_step,
    get_booking_progress_summary
)


class TestGetNextIncompleteStep:
    """Test get_next_incomplete_step function."""
    
    def test_empty_flow_state_returns_select_property(self):
        """Test that empty flow_state returns select_property as next step."""
        flow_state = {}
        result = get_next_incomplete_step(flow_state)
        assert result == "select_property"
    
    def test_property_selected_returns_select_court(self):
        """Test that with property selected, returns select_court."""
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center"
        }
        result = get_next_incomplete_step(flow_state)
        assert result == "select_court"
    
    def test_property_and_court_selected_returns_select_date(self):
        """Test that with property and court selected, returns select_date."""
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A"
        }
        result = get_next_incomplete_step(flow_state)
        assert result == "select_date"
    
    def test_property_court_date_selected_returns_select_time(self):
        """Test that with property, court, and date selected, returns select_time."""
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25"
        }
        result = get_next_incomplete_step(flow_state)
        assert result == "select_time"
    
    def test_all_data_present_returns_confirm_booking(self):
        """Test that with all data present, returns confirm_booking."""
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "14:00-15:00"
        }
        result = get_next_incomplete_step(flow_state)
        assert result == "confirm_booking"


class TestShouldSkipToNextStep:
    """Test should_skip_to_next_step function."""
    
    def test_select_property_with_property_id_should_skip(self):
        """Test that select_property skips when property_id exists."""
        flow_state = {"property_id": 1, "property_name": "Sports Center"}
        should_skip, next_node = should_skip_to_next_step("select_property", flow_state)
        assert should_skip is True
        assert next_node == "select_court"
    
    def test_select_property_without_property_id_should_not_skip(self):
        """Test that select_property doesn't skip when property_id is missing."""
        flow_state = {}
        should_skip, next_node = should_skip_to_next_step("select_property", flow_state)
        assert should_skip is False
        assert next_node is None
    
    def test_select_court_with_court_id_should_skip(self):
        """Test that select_court skips when court_id exists."""
        flow_state = {
            "property_id": 1,
            "court_id": 10,
            "court_name": "Tennis Court A"
        }
        should_skip, next_node = should_skip_to_next_step("select_court", flow_state)
        assert should_skip is True
        assert next_node == "select_date"
    
    def test_select_date_with_date_should_skip(self):
        """Test that select_date skips when date exists."""
        flow_state = {
            "property_id": 1,
            "court_id": 10,
            "date": "2024-12-25"
        }
        should_skip, next_node = should_skip_to_next_step("select_date", flow_state)
        assert should_skip is True
        assert next_node == "select_time"
    
    def test_select_time_with_time_slot_should_skip(self):
        """Test that select_time skips when time_slot exists."""
        flow_state = {
            "property_id": 1,
            "court_id": 10,
            "date": "2024-12-25",
            "time_slot": "14:00-15:00"
        }
        should_skip, next_node = should_skip_to_next_step("select_time", flow_state)
        assert should_skip is True
        assert next_node == "confirm_booking"


class TestValidateRequiredFieldsForStep:
    """Test validate_required_fields_for_step function."""
    
    def test_select_property_has_no_prerequisites(self):
        """Test that select_property has no prerequisites."""
        flow_state = {}
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "select_property",
            flow_state
        )
        assert is_valid is True
        assert missing_field is None
        assert redirect_node is None
    
    def test_select_court_requires_property_id(self):
        """Test that select_court requires property_id."""
        flow_state = {}
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "select_court",
            flow_state
        )
        assert is_valid is False
        assert missing_field == "property_id"
        assert redirect_node == "select_property"
    
    def test_select_court_valid_with_property_id(self):
        """Test that select_court is valid with property_id."""
        flow_state = {"property_id": 1}
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "select_court",
            flow_state
        )
        assert is_valid is True
        assert missing_field is None
        assert redirect_node is None
    
    def test_select_date_requires_property_and_court(self):
        """Test that select_date requires both property_id and court_id."""
        # Missing both
        flow_state = {}
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "select_date",
            flow_state
        )
        assert is_valid is False
        assert missing_field == "property_id"
        
        # Missing court_id
        flow_state = {"property_id": 1}
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "select_date",
            flow_state
        )
        assert is_valid is False
        assert missing_field == "court_id"
        assert redirect_node == "select_court"
    
    def test_select_time_requires_property_court_and_date(self):
        """Test that select_time requires property_id, court_id, and date."""
        # Missing date
        flow_state = {"property_id": 1, "court_id": 10}
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "select_time",
            flow_state
        )
        assert is_valid is False
        assert missing_field == "date"
        assert redirect_node == "select_date"
    
    def test_confirm_booking_requires_all_fields(self):
        """Test that confirm_booking requires all booking fields."""
        # Missing time_slot
        flow_state = {
            "property_id": 1,
            "court_id": 10,
            "date": "2024-12-25"
        }
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "confirm_booking",
            flow_state
        )
        assert is_valid is False
        assert missing_field == "time_slot"
        assert redirect_node == "select_time"
        
        # All fields present
        flow_state = {
            "property_id": 1,
            "court_id": 10,
            "date": "2024-12-25",
            "time_slot": "14:00-15:00"
        }
        is_valid, missing_field, redirect_node = validate_required_fields_for_step(
            "confirm_booking",
            flow_state
        )
        assert is_valid is True
        assert missing_field is None
        assert redirect_node is None


class TestGetBookingProgressSummary:
    """Test get_booking_progress_summary function."""
    
    def test_empty_flow_state_shows_zero_progress(self):
        """Test that empty flow_state shows 0% progress."""
        flow_state = {}
        summary = get_booking_progress_summary(flow_state)
        
        assert summary["property_selected"] is False
        assert summary["court_selected"] is False
        assert summary["date_selected"] is False
        assert summary["time_selected"] is False
        assert summary["completion_percentage"] == 0
        assert summary["completed_steps"] == 0
        assert summary["total_steps"] == 4
        assert summary["next_step"] == "select_property"
    
    def test_property_selected_shows_25_percent_progress(self):
        """Test that property selected shows 25% progress."""
        flow_state = {"property_id": 1, "property_name": "Sports Center"}
        summary = get_booking_progress_summary(flow_state)
        
        assert summary["property_selected"] is True
        assert summary["court_selected"] is False
        assert summary["date_selected"] is False
        assert summary["time_selected"] is False
        assert summary["completion_percentage"] == 25
        assert summary["completed_steps"] == 1
        assert summary["next_step"] == "select_court"
    
    def test_property_and_court_selected_shows_50_percent_progress(self):
        """Test that property and court selected shows 50% progress."""
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A"
        }
        summary = get_booking_progress_summary(flow_state)
        
        assert summary["property_selected"] is True
        assert summary["court_selected"] is True
        assert summary["date_selected"] is False
        assert summary["time_selected"] is False
        assert summary["completion_percentage"] == 50
        assert summary["completed_steps"] == 2
        assert summary["next_step"] == "select_date"
    
    def test_all_data_present_shows_100_percent_progress(self):
        """Test that all data present shows 100% progress."""
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "14:00-15:00"
        }
        summary = get_booking_progress_summary(flow_state)
        
        assert summary["property_selected"] is True
        assert summary["court_selected"] is True
        assert summary["date_selected"] is True
        assert summary["time_selected"] is True
        assert summary["completion_percentage"] == 100
        assert summary["completed_steps"] == 4
        assert summary["next_step"] == "confirm_booking"


class TestValidateBookingFlowSequence:
    """Test validate_booking_flow_sequence function."""
    
    def test_select_property_valid_when_no_data(self):
        """Test that select_property is valid when no data exists."""
        is_valid, redirect = validate_booking_flow_sequence("select_property", {})
        assert is_valid is True
        assert redirect is None
    
    def test_select_property_invalid_when_property_exists(self):
        """Test that select_property is invalid when property already exists."""
        flow_state = {"property_id": 1, "property_name": "Sports Center"}
        is_valid, redirect = validate_booking_flow_sequence("select_property", flow_state)
        assert is_valid is False
        assert redirect == "select_court"
    
    def test_select_court_invalid_when_no_property(self):
        """Test that select_court is invalid when property doesn't exist."""
        is_valid, redirect = validate_booking_flow_sequence("select_court", {})
        assert is_valid is False
        assert redirect == "select_property"
    
    def test_select_court_valid_when_property_exists(self):
        """Test that select_court is valid when property exists."""
        flow_state = {"property_id": 1, "property_name": "Sports Center"}
        is_valid, redirect = validate_booking_flow_sequence("select_court", flow_state)
        assert is_valid is True
        assert redirect is None
    
    def test_select_time_invalid_when_date_missing(self):
        """Test that select_time is invalid when date is missing."""
        flow_state = {"property_id": 1, "court_id": 10}
        is_valid, redirect = validate_booking_flow_sequence("select_time", flow_state)
        assert is_valid is False
        assert redirect == "select_date"
