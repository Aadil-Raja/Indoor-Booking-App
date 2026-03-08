"""
Flow execution logger - logs each node execution with input and output.

Creates a unique log file per chat_id that gets cleared on each new request.
Logs the complete flow from first agent node to last node execution.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FlowLogger:
    """
    Logs flow execution for debugging and monitoring.
    
    Creates a log file per chat_id in logs/flows/{chat_id}.log
    Each new request clears the previous log.
    """
    
    def __init__(self, log_dir: str = "logs/flows"):
        """
        Initialize flow logger.
        
        Args:
            log_dir: Directory to store flow logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_chat_id = None
        self._log_file = None
    
    def start_request(self, chat_id: str, user_message: str):
        """
        Start logging a new request - clears previous log for this chat.
        
        Args:
            chat_id: Chat ID for this request
            user_message: User's message that triggered this flow
        """
        self._current_chat_id = chat_id
        self._log_file = self.log_dir / f"{chat_id}.log"
        
        # Clear previous log
        with open(self._log_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*80}\n")
            f.write(f"FLOW EXECUTION LOG\n")
            f.write(f"Chat ID: {chat_id}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"User Message: {user_message}\n")
            f.write(f"{'='*80}\n\n")
        
        logger.info(f"Started flow logging for chat {chat_id}")
    
    def log_node(
        self,
        node_name: str,
        input_state: Dict[str, Any],
        output_state: Dict[str, Any],
        duration_ms: Optional[float] = None
    ):
        """
        Log a node execution with input and output state.
        
        Args:
            node_name: Name of the node that executed
            input_state: State before node execution
            output_state: State after node execution
            duration_ms: Execution duration in milliseconds
        """
        if not self._log_file:
            logger.warning("Flow logger not initialized, skipping log")
            return
        
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'─'*80}\n")
                f.write(f"NODE: {node_name}\n")
                if duration_ms:
                    f.write(f"Duration: {duration_ms:.2f}ms\n")
                f.write(f"{'─'*80}\n\n")
                
                # Log input state (only relevant fields)
                f.write("INPUT STATE:\n")
                f.write(self._format_state(input_state))
                f.write("\n\n")
                
                # Log output state (only relevant fields)
                f.write("OUTPUT STATE:\n")
                f.write(self._format_state(output_state))
                f.write("\n\n")
                
                # Log state changes
                changes = self._detect_changes(input_state, output_state)
                if changes:
                    f.write("STATE CHANGES:\n")
                    for key, (old_val, new_val) in changes.items():
                        f.write(f"  {key}:\n")
                        f.write(f"    Before: {self._format_value(old_val)}\n")
                        f.write(f"    After:  {self._format_value(new_val)}\n")
                    f.write("\n")
        
        except Exception as e:
            logger.error(f"Error logging node {node_name}: {e}", exc_info=True)
    
    def log_error(self, node_name: str, error: Exception):
        """
        Log an error that occurred during node execution.
        
        Args:
            node_name: Name of the node where error occurred
            error: The exception that was raised
        """
        if not self._log_file:
            return
        
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'!'*80}\n")
                f.write(f"ERROR in {node_name}\n")
                f.write(f"{'!'*80}\n")
                f.write(f"{type(error).__name__}: {str(error)}\n\n")
        except Exception as e:
            logger.error(f"Error logging error for {node_name}: {e}")
    
    def end_request(self, final_state: Dict[str, Any]):
        """
        End logging for this request - log final state.
        
        Args:
            final_state: Final state after all nodes executed
        """
        if not self._log_file:
            return
        
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"FINAL STATE\n")
                f.write(f"{'='*80}\n\n")
                f.write(self._format_state(final_state))
                f.write(f"\n\n{'='*80}\n")
                f.write(f"END OF FLOW EXECUTION\n")
                f.write(f"{'='*80}\n")
            
            logger.info(f"Completed flow logging for chat {self._current_chat_id}")
        except Exception as e:
            logger.error(f"Error ending flow log: {e}")
    
    def _format_state(self, state: Dict[str, Any]) -> str:
        """Format state for logging - only include relevant fields."""
        relevant_fields = [
            "chat_id",
            "user_message",
            "intent",
            "response_content",
            "response_type",
            "flow_state",
            "bot_memory"
        ]
        
        formatted = {}
        for field in relevant_fields:
            if field in state:
                formatted[field] = state[field]
        
        return json.dumps(formatted, indent=2, default=str)
    
    def _format_value(self, value: Any) -> str:
        """Format a value for compact display."""
        if value is None:
            return "None"
        elif isinstance(value, (str, int, float, bool)):
            return str(value)
        elif isinstance(value, (list, dict)):
            return json.dumps(value, default=str)
        else:
            return str(value)
    
    def _detect_changes(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> Dict[str, tuple]:
        """
        Detect changes between before and after state.
        
        Returns:
            Dict mapping field name to (old_value, new_value) tuple
        """
        changes = {}
        
        # Check flow_state changes
        before_flow = before.get("flow_state", {})
        after_flow = after.get("flow_state", {})
        
        if before_flow != after_flow:
            for key in set(list(before_flow.keys()) + list(after_flow.keys())):
                old_val = before_flow.get(key)
                new_val = after_flow.get(key)
                
                if old_val != new_val:
                    changes[f"flow_state.{key}"] = (old_val, new_val)
        
        # Check other top-level changes
        for key in ["intent", "response_content", "response_type"]:
            old_val = before.get(key)
            new_val = after.get(key)
            
            if old_val != new_val:
                changes[key] = (old_val, new_val)
        
        return changes


# Global flow logger instance
_flow_logger = FlowLogger()


def get_flow_logger() -> FlowLogger:
    """Get the global flow logger instance."""
    return _flow_logger
