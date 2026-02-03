"""
UTF-8 streaming utilities for safe character handling.
Prevents character truncation at chunk boundaries.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UTF8StreamBuffer:
    """
    Byte-aware buffer for UTF-8 streaming to prevent character truncation.
    
    Handles partial UTF-8 sequences at chunk boundaries, ensuring that
    multi-byte characters (Chinese, emoji, etc.) are not split incorrectly.
    
    Example:
        >>> buffer = UTF8StreamBuffer()
        >>> chunk1 = "你好".encode('utf-8')[:4]  # Partial character
        >>> chunk2 = "你好".encode('utf-8')[4:]
        >>> result1 = buffer.process_chunk(chunk1)
        >>> result2 = buffer.process_chunk(chunk2)
        >>> final = buffer.flush()
        >>> full_text = result1 + result2 + final
    """
    
    def __init__(self):
        """Initialize the buffer with empty state."""
        self.incomplete_bytes = b""
        self._total_bytes_processed = 0
        self._total_chars_output = 0
    
    def process_chunk(self, chunk_bytes: bytes) -> str:
        """
        Process a chunk of bytes, handling partial UTF-8 sequences.
        
        This method buffers incomplete UTF-8 sequences at the end of chunks
        and combines them with the next chunk to ensure valid decoding.
        
        Args:
            chunk_bytes: Raw bytes from streaming response
            
        Returns:
            Valid UTF-8 string, buffering incomplete sequences for next chunk
            
        Raises:
            None - handles all decoding errors gracefully
        """
        if not chunk_bytes:
            return ""
        
        # Prepend any incomplete bytes from previous chunk
        data = self.incomplete_bytes + chunk_bytes
        self._total_bytes_processed += len(chunk_bytes)
        
        # Try to decode, handling incomplete sequences
        try:
            text = data.decode('utf-8')
            self.incomplete_bytes = b""
            self._total_chars_output += len(text)
            return text
        except UnicodeDecodeError as e:
            # Find the start of the incomplete sequence
            valid_end = e.start
            
            if valid_end == 0:
                # Entire chunk is invalid or incomplete
                self.incomplete_bytes = data
                return ""
            
            # Decode the valid portion
            valid_text = data[:valid_end].decode('utf-8')
            self.incomplete_bytes = data[valid_end:]
            self._total_chars_output += len(valid_text)
            
            # Log if buffer is getting too large (potential issue)
            if len(self.incomplete_bytes) > 10:
                logger.warning(
                    f"UTF8StreamBuffer has {len(self.incomplete_bytes)} incomplete bytes. "
                    "This may indicate corrupted stream data."
                )
            
            return valid_text
    
    def flush(self) -> str:
        """
        Flush any remaining incomplete bytes.
        
        Should be called at end of stream to ensure all buffered data
        is processed. Uses error replacement for truly invalid sequences.
        
        Returns:
            Remaining buffered content (may be empty or contain replacement char)
        """
        if not self.incomplete_bytes:
            return ""
        
        # Try to decode remaining bytes with error handling
        try:
            text = self.incomplete_bytes.decode('utf-8')
            self.incomplete_bytes = b""
            self._total_chars_output += len(text)
            return text
        except UnicodeDecodeError:
            # Replace invalid sequences with Unicode replacement character
            logger.warning(
                f"Flushing {len(self.incomplete_bytes)} invalid UTF-8 bytes "
                "at end of stream. Using replacement character."
            )
            text = self.incomplete_bytes.decode('utf-8', errors='replace')
            self.incomplete_bytes = b""
            self._total_chars_output += len(text)
            return text
    
    def reset(self) -> None:
        """
        Reset the buffer state.
        
        Should be called between independent streams to ensure
        clean state.
        """
        if self.incomplete_bytes:
            logger.warning(
                f"Resetting buffer with {len(self.incomplete_bytes)} "
                "incomplete bytes. Data may be lost."
            )
        self.incomplete_bytes = b""
        self._total_bytes_processed = 0
        self._total_chars_output = 0
    
    def get_stats(self) -> dict:
        """
        Get buffer statistics for monitoring.
        
        Returns:
            Dictionary with buffer statistics
        """
        return {
            "total_bytes_processed": self._total_bytes_processed,
            "total_chars_output": self._total_chars_output,
            "incomplete_bytes_buffered": len(self.incomplete_bytes),
            "compression_ratio": (
                self._total_chars_output / self._total_bytes_processed
                if self._total_bytes_processed > 0
                else 0
            )
        }


class StreamingErrorRecovery:
    """
    Error recovery mechanisms for streaming failures.
    
    Provides exponential backoff retry logic and fallback strategies
    for handling streaming interruptions.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize error recovery.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._retry_count = 0
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if error is retryable.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if should retry, False otherwise
        """
        # Retryable errors: network issues, timeouts
        retryable_types = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
        
        if not isinstance(error, retryable_types):
            return False
        
        if self._retry_count >= self.max_retries:
            logger.warning(
                f"Max retries ({self.max_retries}) reached. "
                "Not retrying further."
            )
            return False
        
        return True
    
    def get_retry_delay(self) -> float:
        """
        Get delay before next retry using exponential backoff.
        
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (2 ** self._retry_count)
        self._retry_count += 1
        return delay
    
    def reset(self) -> None:
        """Reset retry counter."""
        self._retry_count = 0
