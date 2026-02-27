"""
Unit tests for select_time node.

This module tests the select_time node functionality including:
- Time slot retrieval with pricing
- Time slot presentation as list
- Time selection parsing
- Flow state updates
- Error handling for invalid selections
"""

import pytest
from datetime import datetime, date, time
from unittest.mock import AsyncMock, MagicMock, patch

from .select_time import (
    select_time,
    _parse_time_selection,
    _format_time_for_display,
    _format_slots_as_list,
    _present_time_options,
    _process_time_selection
)


class TestSelectTime:
    """Test suite for select_time node"""
    
    @pytest.mark.asyncio
    async def test_time_already_selected(self):
        """Test that node skips processing if time already selected"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "14:00",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "date": "2024-12-25",
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "step": "time_selected"
            }
        }
        
        result = await select_time(state)
        
        # Should return state unchanged
        assert result["flow_state"]["start_time"] == "14:00:00"
        assert result["flow_state"]["end_time"] == "15:00:00"
        assert result["flow_state"]["step"] == "time_selected"
    
    @pytest.mark.asyncio
    async def test_no_date_selected(self):
        """Test error handling when date not selected"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "14:00",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "step": "service_selected"
            }
        }
        
        result = await select_time(state)
        
        assert "select a date first" in result["response_content"].lower()
        assert result["response_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_no_service_selected(self):
        """Test error handling when service not selected"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "14:00",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "date": "2024-12-25",
                "step": "date_selected"
            }
        }
        
        result = await select_time(state)
        
        assert "select a court first" in result["response_content"].lower()
        assert result["response_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_present_time_options_success(self):
        """Test presenting time slot options with pricing"""
        mock_tools = {
            "get_available_slots": AsyncMock(return_value={
                "date": "2024-12-25",
                "court_id": 10,
                "court_name": "Tennis Court A",
                "available_slots": [
                    {
                        "start_time": "09:00:00",
                        "end_time": "10:00:00",
                        "price_per_hour": 50.0,
                        "label": "Morning Rate"
                    },
                    {
                        "start_time": "14:00:00",
                        "end_time": "15:00:00",
                        "price_per_hour": 75.0,
                        "label": "Afternoon Rate"
                    }
                ]
            })
        }
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "2024-12-25",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "date": "2024-12-25",
                "step": "date_selected"
            },
            "bot_memory": {}
        }
        
        result = await select_time(state, tools=mock_tools)
        
        assert result["response_type"] == "list"
        assert "list_items" in result["response_metadata"]
        assert len(result["response_metadata"]["list_items"]) == 2
        assert result["flow_state"]["step"] == "select_time"
        
        # Check list items format
        list_items = result["response_metadata"]["list_items"]
        assert list_items[0]["id"] == "09:00:00"
        assert "9:00 AM" in list_items[0]["title"]
        assert "$50.00/hour" in list_items[0]["description"]
        assert "Morning Rate" in list_items[0]["description"]
    
    @pytest.mark.asyncio
    async def test_present_time_options_no_slots(self):
        """Test handling when no time slots are available"""
        mock_tools = {
            "get_available_slots": AsyncMock(return_value={
                "date": "2024-12-25",
                "court_id": 10,
                "court_name": "Tennis Court A",
                "available_slots": []
            })
        }
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "2024-12-25",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "date": "2024-12-25",
                "step": "date_selected"
            },
            "bot_memory": {}
        }
        
        result = await select_time(state, tools=mock_tools)
        
        assert "no available time slots" in result["response_content"].lower()
        assert "different date" in result["response_content"].lower()
        assert result["response_type"] == "text"
        assert result["flow_state"]["step"] == "date_selected"
    
    @pytest.mark.asyncio
    async def test_valid_time_selection(self):
        """Test valid time slot selection"""
        available_slots = [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Morning Rate"
            },
            {
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "price_per_hour": 75.0,
                "label": "Afternoon Rate"
            }
        ]
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "14:00",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "date": "2024-12-25",
                "step": "select_time"
            },
            "bot_memory": {
                "context": {
                    "slot_details": available_slots
                }
            }
        }
        
        result = await select_time(state)
        
        assert result["flow_state"]["start_time"] == "14:00:00"
        assert result["flow_state"]["end_time"] == "15:00:00"
        assert result["flow_state"]["price"] == 75.0
        assert result["flow_state"]["price_label"] == "Afternoon Rate"
        assert result["flow_state"]["step"] == "time_selected"
        assert "perfect" in result["response_content"].lower()
        assert "$75.00/hour" in result["response_content"]
    
    @pytest.mark.asyncio
    async def test_invalid_time_selection(self):
        """Test error handling for invalid time selection"""
        available_slots = [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Morning Rate"
            }
        ]
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "18:00",  # Not available
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "date": "2024-12-25",
                "step": "select_time"
            },
            "bot_memory": {
                "context": {
                    "slot_details": available_slots
                }
            }
        }
        
        result = await select_time(state)
        
        assert "couldn't find that time slot" in result["response_content"].lower()
        assert result["response_type"] == "text"
        assert result["flow_state"]["step"] == "select_time"
        assert "start_time" not in result["flow_state"]
    
    @pytest.mark.asyncio
    async def test_invalid_date_format_in_flow_state(self):
        """Test error handling for invalid date format in flow_state"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "14:00",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "date": "invalid-date",
                "step": "date_selected"
            },
            "bot_memory": {}
        }
        
        result = await select_time(state)
        
        assert "error with the selected date" in result["response_content"].lower()
        assert result["response_type"] == "text"
        assert result["flow_state"]["step"] == "service_selected"


class TestParseTimeSelection:
    """Test suite for _parse_time_selection helper function"""
    
    def test_parse_exact_start_time(self):
        """Test parsing exact start time match"""
        slots = [
            {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 50.0}
        ]
        
        result = _parse_time_selection("14:00:00", slots)
        assert result == slots[0]
        
        result = _parse_time_selection("14:00", slots)
        assert result == slots[0]
    
    def test_parse_time_with_am_pm(self):
        """Test parsing time with AM/PM"""
        slots = [
            {"start_time": "09:00:00", "end_time": "10:00:00", "price_per_hour": 50.0},
            {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 75.0}
        ]
        
        result = _parse_time_selection("9:00 AM", slots)
        assert result == slots[0]
        
        result = _parse_time_selection("2:00 PM", slots)
        assert result == slots[1]
        
        result = _parse_time_selection("2 pm", slots)
        assert result == slots[1]
    
    def test_parse_by_index(self):
        """Test parsing by slot index"""
        slots = [
            {"start_time": "09:00:00", "end_time": "10:00:00", "price_per_hour": 50.0},
            {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 75.0},
            {"start_time": "16:00:00", "end_time": "17:00:00", "price_per_hour": 75.0}
        ]
        
        result = _parse_time_selection("1", slots)
        assert result == slots[0]
        
        result = _parse_time_selection("first", slots)
        assert result == slots[0]
        
        result = _parse_time_selection("2nd", slots)
        assert result == slots[1]
        
        result = _parse_time_selection("third", slots)
        assert result == slots[2]
    
    def test_parse_time_range(self):
        """Test parsing time range"""
        slots = [
            {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 75.0}
        ]
        
        result = _parse_time_selection("2:00 PM - 3:00 PM", slots)
        assert result == slots[0]
        
        result = _parse_time_selection("14:00 - 15:00", slots)
        assert result == slots[0]
    
    def test_parse_empty_input(self):
        """Test parsing empty input"""
        slots = [
            {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 75.0}
        ]
        
        result = _parse_time_selection("", slots)
        assert result is None
        
        result = _parse_time_selection("   ", slots)
        assert result is None
    
    def test_parse_invalid_input(self):
        """Test parsing invalid input"""
        slots = [
            {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 75.0}
        ]
        
        result = _parse_time_selection("not a time", slots)
        assert result is None
        
        result = _parse_time_selection("25:00", slots)
        assert result is None
    
    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive"""
        slots = [
            {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 75.0}
        ]
        
        result1 = _parse_time_selection("2:00 PM", slots)
        result2 = _parse_time_selection("2:00 pm", slots)
        result3 = _parse_time_selection("2:00 Pm", slots)
        
        assert result1 == result2 == result3 == slots[0]


class TestFormatTimeForDisplay:
    """Test suite for _format_time_for_display helper function"""
    
    def test_format_morning_time(self):
        """Test formatting morning times"""
        assert _format_time_for_display("09:00:00") == "9:00 AM"
        assert _format_time_for_display("09:30:00") == "9:30 AM"
        assert _format_time_for_display("11:45:00") == "11:45 AM"
    
    def test_format_afternoon_time(self):
        """Test formatting afternoon times"""
        assert _format_time_for_display("14:00:00") == "2:00 PM"
        assert _format_time_for_display("15:30:00") == "3:30 PM"
        assert _format_time_for_display("18:45:00") == "6:45 PM"
    
    def test_format_noon(self):
        """Test formatting noon"""
        assert _format_time_for_display("12:00:00") == "12:00 PM"
        assert _format_time_for_display("12:30:00") == "12:30 PM"
    
    def test_format_midnight(self):
        """Test formatting midnight"""
        assert _format_time_for_display("00:00:00") == "12:00 AM"
        assert _format_time_for_display("00:30:00") == "12:30 AM"
    
    def test_format_with_zero_minutes(self):
        """Test formatting times with zero minutes"""
        assert _format_time_for_display("09:00:00") == "9:00 AM"
        assert _format_time_for_display("14:00:00") == "2:00 PM"
    
    def test_format_with_non_zero_minutes(self):
        """Test formatting times with non-zero minutes"""
        assert _format_time_for_display("09:15:00") == "9:15 AM"
        assert _format_time_for_display("14:45:00") == "2:45 PM"
    
    def test_format_invalid_time(self):
        """Test formatting invalid time string"""
        # Should return original string if parsing fails
        result = _format_time_for_display("invalid")
        assert result == "invalid"


class TestFormatSlotsAsList:
    """Test suite for _format_slots_as_list helper function"""
    
    def test_format_single_slot(self):
        """Test formatting a single slot"""
        slots = [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Morning Rate"
            }
        ]
        
        result = _format_slots_as_list(slots)
        
        assert len(result) == 1
        assert result[0]["id"] == "09:00:00"
        assert "9:00 AM" in result[0]["title"]
        assert "10:00 AM" in result[0]["title"]
        assert "$50.00/hour" in result[0]["description"]
        assert "Morning Rate" in result[0]["description"]
    
    def test_format_multiple_slots(self):
        """Test formatting multiple slots"""
        slots = [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Morning Rate"
            },
            {
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "price_per_hour": 75.0,
                "label": "Afternoon Rate"
            }
        ]
        
        result = _format_slots_as_list(slots)
        
        assert len(result) == 2
        assert result[0]["id"] == "09:00:00"
        assert result[1]["id"] == "14:00:00"
        assert "$50.00/hour" in result[0]["description"]
        assert "$75.00/hour" in result[1]["description"]
    
    def test_format_slot_without_label(self):
        """Test formatting slot without label"""
        slots = [
            {
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "price_per_hour": 60.0,
                "label": ""
            }
        ]
        
        result = _format_slots_as_list(slots)
        
        assert len(result) == 1
        assert "$60.00/hour" in result[0]["description"]
        # Should not have parentheses if no label
        assert "(" not in result[0]["description"]
    
    def test_format_empty_slots(self):
        """Test formatting empty slots list"""
        result = _format_slots_as_list([])
        assert result == []
    
    def test_format_slot_with_half_hour(self):
        """Test formatting slot with half-hour times"""
        slots = [
            {
                "start_time": "09:30:00",
                "end_time": "10:30:00",
                "price_per_hour": 55.0,
                "label": "Peak Rate"
            }
        ]
        
        result = _format_slots_as_list(slots)
        
        assert "9:30 AM" in result[0]["title"]
        assert "10:30 AM" in result[0]["title"]
        assert "$55.00/hour" in result[0]["description"]


class TestPresentTimeOptions:
    """Test suite for _present_time_options helper function"""
    
    @pytest.mark.asyncio
    async def test_present_options_with_slots(self):
        """Test presenting options when slots are available"""
        mock_tools = {
            "get_available_slots": AsyncMock(return_value={
                "available_slots": [
                    {
                        "start_time": "09:00:00",
                        "end_time": "10:00:00",
                        "price_per_hour": 50.0,
                        "label": "Morning Rate"
                    }
                ]
            })
        }
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "",
            "flow_state": {
                "service_id": "10",
                "service_name": "Tennis Court A",
                "date": "2024-12-25"
            },
            "bot_memory": {}
        }
        
        result = await _present_time_options(
            state, mock_tools, "test-chat-123",
            state["flow_state"], state["bot_memory"],
            "10", "2024-12-25"
        )
        
        assert result["response_type"] == "list"
        assert result["flow_state"]["step"] == "select_time"
        assert "slot_details" in result["bot_memory"]["context"]
    
    @pytest.mark.asyncio
    async def test_present_options_no_slots(self):
        """Test presenting options when no slots available"""
        mock_tools = {
            "get_available_slots": AsyncMock(return_value={
                "available_slots": []
            })
        }
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "",
            "flow_state": {
                "service_id": "10",
                "service_name": "Tennis Court A",
                "date": "2024-12-25"
            },
            "bot_memory": {}
        }
        
        result = await _present_time_options(
            state, mock_tools, "test-chat-123",
            state["flow_state"], state["bot_memory"],
            "10", "2024-12-25"
        )
        
        assert "no available time slots" in result["response_content"].lower()
        assert result["flow_state"]["step"] == "date_selected"


class TestProcessTimeSelection:
    """Test suite for _process_time_selection helper function"""
    
    @pytest.mark.asyncio
    async def test_process_valid_selection(self):
        """Test processing a valid time selection"""
        available_slots = [
            {
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "price_per_hour": 75.0,
                "label": "Afternoon Rate"
            }
        ]
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "14:00",
            "flow_state": {
                "service_name": "Tennis Court A",
                "date": "2024-12-25",
                "step": "select_time"
            },
            "bot_memory": {
                "context": {
                    "slot_details": available_slots
                }
            }
        }
        
        result = await _process_time_selection(
            state, {}, "test-chat-123", "14:00",
            state["flow_state"], state["bot_memory"]
        )
        
        assert result["flow_state"]["start_time"] == "14:00:00"
        assert result["flow_state"]["end_time"] == "15:00:00"
        assert result["flow_state"]["price"] == 75.0
        assert result["flow_state"]["step"] == "time_selected"
    
    @pytest.mark.asyncio
    async def test_process_invalid_selection(self):
        """Test processing an invalid time selection"""
        available_slots = [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Morning Rate"
            }
        ]
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "18:00",
            "flow_state": {
                "service_name": "Tennis Court A",
                "date": "2024-12-25",
                "step": "select_time"
            },
            "bot_memory": {
                "context": {
                    "slot_details": available_slots
                }
            }
        }
        
        result = await _process_time_selection(
            state, {}, "test-chat-123", "18:00",
            state["flow_state"], state["bot_memory"]
        )
        
        assert "couldn't find that time slot" in result["response_content"].lower()
        assert "start_time" not in result["flow_state"]
        assert result["flow_state"]["step"] == "select_time"
