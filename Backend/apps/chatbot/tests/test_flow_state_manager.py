"""
Unit tests for flow state manager.

This module tests the flow_state management functions that handle temporary
conversation state including current intent, booking progress, and cached data.

Requirements: 3.1, 3.9, 15.1, 15.5, 16.1-16.6
"""

import pytest
from typing import Dict, Any

# Import flow state manager to test
import sys
from pathlib import Path

# Add Backend path for imports
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from apps.chatbot.app.agent.state.flow_state_manager import (
    initialize_flow_state,
    validate_flow_state,
    update_flow_state,
    clear_flow_state,
    clear_booking_field
)


class TestInitializeFlowState:
    """Tests for initialize_flow_state function."""
    
    def test_initialize_returns_dict(self):
        """Test that initialize_flow_state returns a dictionary."""
        flow_state = initialize_flow_state()
        assert isinstance(flow_state, dict)
    
    def test_initialize_has_all_required_fields(self):
        """Test that initialized flow_state has all required fields."""
        flow_state = initialize_flow_state()
        
        required_fields = [
            "current_intent",
            "property_id",
            "property_name",
            "court_id",
            "court_name",
            "date",
            "time_slot",
            "booking_step",
            "owner_properties",
            "context"
        ]
        
        for field in required_fields:
            assert field in flow_state
    
    def test_initialize_sets_none_values(self):
        """Test that most fields are initialized to None."""
        flow_state = initialize_flow_state()
        
        assert flow_state["current_intent"] is None
        assert flow_state["property_id"] is None
        assert flow_state["property_name"] is None
        assert flow_state["court_id"] is None
        assert flow_state["court_name"] is None
        assert flow_state["date"] is None
        assert flow_state["time_slot"] is None
        assert flow_state["booking_step"] is None
        assert flow_state["owner_properties"] is None
    
    def test_initialize_sets_empty_context(self):
        """Test that context is initialized to empty dict."""
        flow_state = initialize_flow_state()
        assert flow_state["context"] == {}


class TestValidateFlowState:
    """Tests for validate_flow_state function."""
    
    def test_validate_valid_flow_state(self):
        """Test validation passes for valid flow_state."""
        flow_state = initialize_flow_state()
        assert validate_flow_state(flow_state) is True
    
    def test_validate_rejects_non_dict(self):
        """Test validation fails for non-dict input."""
        assert validate_flow_state("not a dict") is False
        assert validate_flow_state(None) is False
        assert validate_flow_state([]) is False
    
    def test_validate_rejects_missing_fields(self):
        """Test validation fails when required fields are missing."""
        incomplete_state = {
            "current_intent": "booking",
            "property_id": 123
            # Missing other required fields
        }
        assert validate_flow_state(incomplete_state) is False
    
    def test_validate_allows_extra_fields(self):
        """Test validation allows extra fields for forward compatibility."""
        flow_state = initialize_flow_state()
        flow_state["extra_field"] = "extra_value"
        assert validate_flow_state(flow_state) is True
    
    def test_validate_rejects_invalid_context_type(self):
        """Test validation fails when context is not a dict."""
        flow_state = initialize_flow_state()
        flow_state["context"] = "not a dict"
        assert validate_flow_state(flow_state) is False


class TestUpdateFlowState:
    """Tests for update_flow_state function."""
    
    def test_update_merges_simple_fields(self):
        """Test that simple field updates are merged correctly."""
        current = initialize_flow_state()
        updates = {
            "property_id": 123,
            "property_name": "Test Property"
        }
        
        updated = update_flow_state(current, updates)
        
        assert updated["property_id"] == 123
        assert updated["property_name"] == "Test Property"
    
    def test_update_preserves_existing_fields(self):
        """Test that existing fields are preserved during update."""
        current = initialize_flow_state()
        current["property_id"] = 123
        current["court_id"] = 456
        
        updates = {"date": "2024-01-15"}
        
        updated = update_flow_state(current, updates)
        
        assert updated["property_id"] == 123
        assert updated["court_id"] == 456
        assert updated["date"] == "2024-01-15"
    
    def test_update_deep_merges_context(self):
        """Test that context field is deep merged."""
        current = initialize_flow_state()
        current["context"] = {"key1": "value1", "key2": "value2"}
        
        updates = {"context": {"key2": "updated", "key3": "value3"}}
        
        updated = update_flow_state(current, updates)
        
        assert updated["context"]["key1"] == "value1"
        assert updated["context"]["key2"] == "updated"
        assert updated["context"]["key3"] == "value3"
    
    def test_update_handles_invalid_current_state(self):
        """Test that invalid current state is reinitialized."""
        current = "not a dict"
        updates = {"property_id": 123}
        
        updated = update_flow_state(current, updates)
        
        assert isinstance(updated, dict)
        assert updated["property_id"] == 123
    
    def test_update_handles_invalid_updates(self):
        """Test that invalid updates are skipped."""
        current = initialize_flow_state()
        current["property_id"] = 123
        
        updated = update_flow_state(current, "not a dict")
        
        assert updated["property_id"] == 123


class TestClearFlowState:
    """Tests for clear_flow_state function."""
    
    def test_clear_returns_empty_state(self):
        """Test that clear_flow_state returns an empty initialized state."""
        cleared = clear_flow_state()
        
        assert isinstance(cleared, dict)
        assert cleared["current_intent"] is None
        assert cleared["property_id"] is None
        assert cleared["date"] is None
    
    def test_clear_is_equivalent_to_initialize(self):
        """Test that clear_flow_state returns same structure as initialize."""
        cleared = clear_flow_state()
        initialized = initialize_flow_state()
        
        assert cleared == initialized


class TestClearBookingField:
    """Tests for clear_booking_field function."""
    
    def test_clear_property_clears_all_downstream(self):
        """Test that clearing property clears all downstream fields."""
        flow_state = initialize_flow_state()
        flow_state["property_id"] = 123
        flow_state["property_name"] = "Test Property"
        flow_state["court_id"] = 456
        flow_state["court_name"] = "Court A"
        flow_state["date"] = "2024-01-15"
        flow_state["time_slot"] = "10:00-11:00"
        flow_state["booking_step"] = "time_selected"
        
        updated = clear_booking_field(flow_state, "property")
        
        assert updated["property_id"] is None
        assert updated["property_name"] is None
        assert updated["court_id"] is None
        assert updated["court_name"] is None
        assert updated["date"] is None
        assert updated["time_slot"] is None
        assert updated["booking_step"] is None
    
    def test_clear_court_clears_downstream_only(self):
        """Test that clearing court preserves property but clears downstream."""
        flow_state = initialize_flow_state()
        flow_state["property_id"] = 123
        flow_state["property_name"] = "Test Property"
        flow_state["court_id"] = 456
        flow_state["court_name"] = "Court A"
        flow_state["date"] = "2024-01-15"
        flow_state["time_slot"] = "10:00-11:00"
        flow_state["booking_step"] = "time_selected"
        
        updated = clear_booking_field(flow_state, "court")
        
        # Property preserved
        assert updated["property_id"] == 123
        assert updated["property_name"] == "Test Property"
        
        # Court and downstream cleared
        assert updated["court_id"] is None
        assert updated["court_name"] is None
        assert updated["date"] is None
        assert updated["time_slot"] is None
        assert updated["booking_step"] == "property_selected"
    
    def test_clear_date_clears_downstream_only(self):
        """Test that clearing date preserves property and court."""
        flow_state = initialize_flow_state()
        flow_state["property_id"] = 123
        flow_state["property_name"] = "Test Property"
        flow_state["court_id"] = 456
        flow_state["court_name"] = "Court A"
        flow_state["date"] = "2024-01-15"
        flow_state["time_slot"] = "10:00-11:00"
        flow_state["booking_step"] = "time_selected"
        
        updated = clear_booking_field(flow_state, "date")
        
        # Property and court preserved
        assert updated["property_id"] == 123
        assert updated["property_name"] == "Test Property"
        assert updated["court_id"] == 456
        assert updated["court_name"] == "Court A"
        
        # Date and downstream cleared
        assert updated["date"] is None
        assert updated["time_slot"] is None
        assert updated["booking_step"] == "court_selected"
    
    def test_clear_time_slot_preserves_all_upstream(self):
        """Test that clearing time_slot preserves all upstream fields."""
        flow_state = initialize_flow_state()
        flow_state["property_id"] = 123
        flow_state["property_name"] = "Test Property"
        flow_state["court_id"] = 456
        flow_state["court_name"] = "Court A"
        flow_state["date"] = "2024-01-15"
        flow_state["time_slot"] = "10:00-11:00"
        flow_state["booking_step"] = "time_selected"
        
        updated = clear_booking_field(flow_state, "time_slot")
        
        # All upstream preserved
        assert updated["property_id"] == 123
        assert updated["property_name"] == "Test Property"
        assert updated["court_id"] == 456
        assert updated["court_name"] == "Court A"
        assert updated["date"] == "2024-01-15"
        
        # Only time_slot cleared
        assert updated["time_slot"] is None
        assert updated["booking_step"] == "date_selected"
    
    def test_clear_unknown_field_does_nothing(self):
        """Test that clearing unknown field doesn't modify state."""
        flow_state = initialize_flow_state()
        flow_state["property_id"] = 123
        
        updated = clear_booking_field(flow_state, "unknown_field")
        
        assert updated["property_id"] == 123
    
    def test_clear_handles_invalid_state(self):
        """Test that clearing handles invalid state gracefully."""
        invalid_state = "not a dict"
        
        updated = clear_booking_field(invalid_state, "property")
        
        # Should return the invalid state unchanged
        assert updated == invalid_state
