"""
Unit tests for select_date node.

This module tests the select_date node functionality including:
- Date parsing from various formats
- Date validation (future dates only)
- Flow state updates
- Error handling for invalid dates
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from .select_date import select_date, _parse_date, _prompt_for_date, _process_date_selection


class TestSelectDate:
    """Test suite for select_date node"""
    
    @pytest.mark.asyncio
    async def test_date_already_selected(self):
        """Test that node skips processing if date already selected"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "tomorrow",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "date": "2024-12-25",
                "step": "date_selected"
            }
        }
        
        result = await select_date(state)
        
        # Should return state unchanged
        assert result["flow_state"]["date"] == "2024-12-25"
        assert result["flow_state"]["step"] == "date_selected"
    
    @pytest.mark.asyncio
    async def test_no_service_selected(self):
        """Test error handling when service not selected"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "tomorrow",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "step": "property_selected"
            }
        }
        
        result = await select_date(state)
        
        assert "select a court first" in result["response_content"].lower()
        assert result["response_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_prompt_for_date(self):
        """Test initial date prompt"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "Tennis Court A",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "step": "service_selected"
            }
        }
        
        result = await select_date(state)
        
        assert "when would you like to book" in result["response_content"].lower()
        assert "tomorrow" in result["response_content"].lower()
        assert result["response_type"] == "text"
        assert result["flow_state"]["step"] == "select_date"
    
    @pytest.mark.asyncio
    async def test_valid_date_selection_tomorrow(self):
        """Test valid date selection with 'tomorrow'"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "tomorrow",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "step": "select_date"
            }
        }
        
        result = await select_date(state)
        
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        expected_date = tomorrow.strftime("%Y-%m-%d")
        
        assert result["flow_state"]["date"] == expected_date
        assert result["flow_state"]["step"] == "date_selected"
        assert "perfect" in result["response_content"].lower()
        assert "time slot" in result["response_content"].lower()
    
    @pytest.mark.asyncio
    async def test_valid_date_selection_iso_format(self):
        """Test valid date selection with ISO format"""
        future_date = (datetime.now() + timedelta(days=7)).date()
        date_str = future_date.strftime("%Y-%m-%d")
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": date_str,
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "step": "select_date"
            }
        }
        
        result = await select_date(state)
        
        assert result["flow_state"]["date"] == date_str
        assert result["flow_state"]["step"] == "date_selected"
    
    @pytest.mark.asyncio
    async def test_invalid_date_format(self):
        """Test error handling for invalid date format"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "some random text",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "step": "select_date"
            }
        }
        
        result = await select_date(state)
        
        assert "couldn't understand" in result["response_content"].lower()
        assert result["response_type"] == "text"
        assert result["flow_state"]["step"] == "select_date"
        assert "date" not in result["flow_state"]
    
    @pytest.mark.asyncio
    async def test_past_date_rejection(self):
        """Test rejection of past dates"""
        past_date = (datetime.now() - timedelta(days=7)).date()
        date_str = past_date.strftime("%Y-%m-%d")
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": date_str,
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "step": "select_date"
            }
        }
        
        result = await select_date(state)
        
        assert "in the past" in result["response_content"].lower()
        assert result["response_type"] == "text"
        assert result["flow_state"]["step"] == "select_date"
        assert "date" not in result["flow_state"]


class TestParseDateFunction:
    """Test suite for _parse_date helper function"""
    
    def test_parse_today(self):
        """Test parsing 'today'"""
        result = _parse_date("today")
        expected = datetime.now().date()
        assert result == expected
    
    def test_parse_tomorrow(self):
        """Test parsing 'tomorrow'"""
        result = _parse_date("tomorrow")
        expected = (datetime.now() + timedelta(days=1)).date()
        assert result == expected
    
    def test_parse_in_x_days(self):
        """Test parsing 'in X days' format"""
        result = _parse_date("in 5 days")
        expected = (datetime.now() + timedelta(days=5)).date()
        assert result == expected
        
        result = _parse_date("in 1 day")
        expected = (datetime.now() + timedelta(days=1)).date()
        assert result == expected
    
    def test_parse_next_weekday(self):
        """Test parsing 'next Monday', 'next Tuesday', etc."""
        result = _parse_date("next Monday")
        assert result is not None
        assert result > datetime.now().date()
        assert result.weekday() == 0  # Monday
        
        result = _parse_date("next Friday")
        assert result is not None
        assert result > datetime.now().date()
        assert result.weekday() == 4  # Friday
    
    def test_parse_weekday_without_next(self):
        """Test parsing weekday names without 'next'"""
        result = _parse_date("Monday")
        assert result is not None
        assert result > datetime.now().date()
        assert result.weekday() == 0  # Monday
    
    def test_parse_iso_format(self):
        """Test parsing ISO format dates"""
        result = _parse_date("2024-12-25")
        assert result == datetime(2024, 12, 25).date()
        
        result = _parse_date("2024/12/25")
        assert result == datetime(2024, 12, 25).date()
    
    def test_parse_numeric_format(self):
        """Test parsing numeric date formats"""
        result = _parse_date("12/25/2024")
        assert result == datetime(2024, 12, 25).date()
        
        result = _parse_date("12/25/24")
        assert result == datetime(2024, 12, 25).date()
    
    def test_parse_month_day_current_year(self):
        """Test parsing MM/DD format (assumes current year)"""
        today = datetime.now().date()
        
        # Use a future month to avoid year rollover issues
        future_month = (today.month % 12) + 1
        future_year = today.year if future_month > today.month else today.year + 1
        
        result = _parse_date(f"{future_month}/15")
        assert result is not None
        assert result.month == future_month
        assert result.day == 15
    
    def test_parse_natural_language_month_day(self):
        """Test parsing natural language dates like 'December 25'"""
        result = _parse_date("December 25")
        assert result is not None
        assert result.month == 12
        assert result.day == 25
        
        result = _parse_date("Dec 25")
        assert result is not None
        assert result.month == 12
        assert result.day == 25
        
        result = _parse_date("25 December")
        assert result is not None
        assert result.month == 12
        assert result.day == 25
    
    def test_parse_natural_language_with_year(self):
        """Test parsing natural language dates with year"""
        result = _parse_date("December 25 2024")
        assert result == datetime(2024, 12, 25).date()
        
        result = _parse_date("25 Dec 2025")
        assert result == datetime(2025, 12, 25).date()
    
    def test_parse_empty_input(self):
        """Test parsing empty input"""
        result = _parse_date("")
        assert result is None
        
        result = _parse_date("   ")
        assert result is None
    
    def test_parse_invalid_input(self):
        """Test parsing invalid input"""
        result = _parse_date("not a date")
        assert result is None
        
        result = _parse_date("xyz123")
        assert result is None
    
    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive"""
        result1 = _parse_date("TOMORROW")
        result2 = _parse_date("tomorrow")
        result3 = _parse_date("ToMoRrOw")
        
        assert result1 == result2 == result3
        
        result1 = _parse_date("NEXT MONDAY")
        result2 = _parse_date("next monday")
        
        assert result1 == result2
    
    def test_parse_abbreviated_weekdays(self):
        """Test parsing abbreviated weekday names"""
        result = _parse_date("next Mon")
        assert result is not None
        assert result.weekday() == 0
        
        result = _parse_date("Fri")
        assert result is not None
        assert result.weekday() == 4
    
    def test_parse_abbreviated_months(self):
        """Test parsing abbreviated month names"""
        result = _parse_date("Jan 15")
        assert result is not None
        assert result.month == 1
        assert result.day == 15
        
        result = _parse_date("Sep 30")
        assert result is not None
        assert result.month == 9
        assert result.day == 30


class TestPromptForDate:
    """Test suite for _prompt_for_date helper function"""
    
    @pytest.mark.asyncio
    async def test_prompt_includes_service_name(self):
        """Test that prompt includes the service name"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "",
            "flow_state": {
                "service_name": "Tennis Court A"
            }
        }
        
        result = await _prompt_for_date(state, "test-chat-123", state["flow_state"])
        
        assert "Tennis Court A" in result["response_content"]
        assert result["flow_state"]["step"] == "select_date"
    
    @pytest.mark.asyncio
    async def test_prompt_includes_examples(self):
        """Test that prompt includes date format examples"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "",
            "flow_state": {
                "service_name": "Court A"
            }
        }
        
        result = await _prompt_for_date(state, "test-chat-123", state["flow_state"])
        
        assert "tomorrow" in result["response_content"].lower()
        assert "next monday" in result["response_content"].lower()


class TestProcessDateSelection:
    """Test suite for _process_date_selection helper function"""
    
    @pytest.mark.asyncio
    async def test_process_valid_date(self):
        """Test processing a valid future date"""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": "tomorrow",
            "flow_state": {
                "service_name": "Tennis Court A",
                "step": "select_date"
            }
        }
        
        result = await _process_date_selection(
            state, "test-chat-123", "tomorrow", state["flow_state"]
        )
        
        assert result["flow_state"]["date"] == tomorrow.strftime("%Y-%m-%d")
        assert result["flow_state"]["step"] == "date_selected"
    
    @pytest.mark.asyncio
    async def test_process_past_date(self):
        """Test processing a past date"""
        past_date = (datetime.now() - timedelta(days=7)).date()
        date_str = past_date.strftime("%Y-%m-%d")
        
        state = {
            "chat_id": "test-chat-123",
            "user_message": date_str,
            "flow_state": {
                "service_name": "Tennis Court A",
                "step": "select_date"
            }
        }
        
        result = await _process_date_selection(
            state, "test-chat-123", date_str, state["flow_state"]
        )
        
        assert "in the past" in result["response_content"].lower()
        assert "date" not in result["flow_state"]
        assert result["flow_state"]["step"] == "select_date"
    
    @pytest.mark.asyncio
    async def test_process_invalid_format(self):
        """Test processing an invalid date format"""
        state = {
            "chat_id": "test-chat-123",
            "user_message": "not a date",
            "flow_state": {
                "service_name": "Tennis Court A",
                "step": "select_date"
            }
        }
        
        result = await _process_date_selection(
            state, "test-chat-123", "not a date", state["flow_state"]
        )
        
        assert "couldn't understand" in result["response_content"].lower()
        assert "date" not in result["flow_state"]
        assert result["flow_state"]["step"] == "select_date"
