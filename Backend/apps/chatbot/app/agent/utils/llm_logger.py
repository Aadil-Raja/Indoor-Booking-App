"""
LLM call logger - logs all LLM prompts and outputs to a file per chat_id.

Creates a log file per chat_id that gets overwritten on each new request.
Logs all LLM calls throughout the flow execution.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMLogger:
    """
    Logs LLM prompts and outputs for debugging and monitoring.
    
    Creates a log file per chat_id in logs/llm/{chat_id}.log
    Each new request overwrites the previous log.
    """
    
    def __init__(self, log_dir: str = "logs/llm"):
        """
        Initialize LLM logger.
        
        Args:
            log_dir: Directory to store LLM logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_chat_id = None
        self._log_file = None
        self._call_counter = 0
    
    def start_request(self, chat_id: str, user_message: str):
        """
        Start logging a new request - overwrites previous log for this chat.
        
        Args:
            chat_id: Chat ID for this request
            user_message: User's message that triggered this flow
        """
        self._current_chat_id = chat_id
        self._log_file = self.log_dir / f"{chat_id}.log"
        self._call_counter = 0
        
        # Overwrite previous log
        with open(self._log_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*80}\n")
            f.write(f"LLM CALL LOG\n")
            f.write(f"Chat ID: {chat_id}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"User Message: {user_message}\n")
            f.write(f"{'='*80}\n\n")
        
        logger.info(f"Started LLM logging for chat {chat_id}")
    
    def log_llm_call(
        self,
        node_name: str,
        prompt: str,
        response: str,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Log an LLM call with prompt and response.
        
        Args:
            node_name: Name of the node making the LLM call
            prompt: The prompt sent to the LLM
            response: The response received from the LLM
            parameters: Optional LLM parameters (temperature, max_tokens, etc.)
        """
        if not self._log_file:
            logger.warning("LLM logger not initialized, skipping log")
            return
        
        self._call_counter += 1
        
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'─'*80}\n")
                f.write(f"LLM CALL #{self._call_counter}: {node_name}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                
                if parameters:
                    f.write(f"Parameters: {parameters}\n")
                
                f.write(f"{'─'*80}\n\n")
                
                # Log prompt
                f.write("PROMPT:\n")
                f.write(f"{'-'*40}\n")
                f.write(f"{prompt}\n")
                f.write(f"{'-'*40}\n\n")
                
                # Log response
                f.write("RESPONSE:\n")
                f.write(f"{'-'*40}\n")
                f.write(f"{response}\n")
                f.write(f"{'-'*40}\n\n")
        
        except Exception as e:
            logger.error(f"Error logging LLM call for {node_name}: {e}", exc_info=True)
    
    def end_request(self):
        """
        End logging for this request.
        """
        if not self._log_file:
            return
        
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"END OF LLM CALLS (Total: {self._call_counter})\n")
                f.write(f"{'='*80}\n")
            
            logger.info(f"Completed LLM logging for chat {self._current_chat_id} ({self._call_counter} calls)")
        except Exception as e:
            logger.error(f"Error ending LLM log: {e}")


# Global LLM logger instance
_llm_logger = LLMLogger()


def get_llm_logger() -> LLMLogger:
    """Get the global LLM logger instance."""
    return _llm_logger
