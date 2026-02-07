"""
Unit tests for UTF-8 streaming safety.
Tests byte-aware buffering to prevent Chinese character truncation.
"""
import pytest
from typing import AsyncGenerator


class UTF8StreamBuffer:
    """
    Byte-aware buffer for UTF-8 streaming to prevent character truncation.
    Handles partial UTF-8 sequences at chunk boundaries.
    """
    
    def __init__(self):
        self.incomplete_bytes = b""
    
    def process_chunk(self, chunk_bytes: bytes) -> str:
        """
        Process a chunk of bytes, handling partial UTF-8 sequences.
        
        Args:
            chunk_bytes: Raw bytes from streaming response
            
        Returns:
            Valid UTF-8 string, buffering incomplete sequences
        """
        # Prepend any incomplete bytes from previous chunk
        data = self.incomplete_bytes + chunk_bytes
        
        # Try to decode, handling incomplete sequences
        try:
            text = data.decode('utf-8')
            self.incomplete_bytes = b""
            return text
        except UnicodeDecodeError as e:
            # Find the start of the incomplete sequence
            valid_end = e.start
            valid_text = data[:valid_end].decode('utf-8')
            self.incomplete_bytes = data[valid_end:]
            return valid_text
    
    def flush(self) -> str:
        """
        Flush any remaining incomplete bytes.
        Should be called at end of stream.
        
        Returns:
            Remaining buffered content (may be empty or replacement char)
        """
        if not self.incomplete_bytes:
            return ""
        
        # Try to decode remaining bytes with error handling
        try:
            text = self.incomplete_bytes.decode('utf-8')
            self.incomplete_bytes = b""
            return text
        except UnicodeDecodeError:
            # Replace invalid sequences
            text = self.incomplete_bytes.decode('utf-8', errors='replace')
            self.incomplete_bytes = b""
            return text


@pytest.mark.asyncio
async def test_chinese_character_boundary():
    """Test handling of Chinese characters split across chunk boundaries."""
    buffer = UTF8StreamBuffer()
    
    # Chinese text: "你好世界" (Hello World)
    full_text = "你好世界"
    full_bytes = full_text.encode('utf-8')
    
    # Split in the middle of a Chinese character (3 bytes per char)
    chunk1 = full_bytes[:5]  # "你好" + 2 bytes of "世"
    chunk2 = full_bytes[5:]  # remaining 1 byte of "世" + "界"
    
    result1 = buffer.process_chunk(chunk1)
    result2 = buffer.process_chunk(chunk2)
    final = buffer.flush()
    
    reconstructed = result1 + result2 + final
    assert reconstructed == full_text, f"Expected '{full_text}', got '{reconstructed}'"


@pytest.mark.asyncio
async def test_partial_utf8_sequence_recovery():
    """Test recovery from partial UTF-8 sequences."""
    buffer = UTF8StreamBuffer()
    
    # Mix of ASCII and Chinese
    text = "Hello 你好 World 世界"
    text_bytes = text.encode('utf-8')
    
    # Split at various positions including mid-character
    chunks = [
        text_bytes[:8],   # "Hello 你" (partial)
        text_bytes[8:15], # rest of "你" + "好 W"
        text_bytes[15:20], # "orld "
        text_bytes[20:23], # "世" (partial)
        text_bytes[23:]    # rest of "世" + "界"
    ]
    
    results = []
    for chunk in chunks:
        result = buffer.process_chunk(chunk)
        if result:
            results.append(result)
    
    final = buffer.flush()
    if final:
        results.append(final)
    
    reconstructed = ''.join(results)
    assert reconstructed == text, f"Expected '{text}', got '{reconstructed}'"


@pytest.mark.asyncio
async def test_streaming_error_recovery():
    """Test error recovery mechanisms for streaming failures."""
    
    async def mock_stream_with_error() -> AsyncGenerator[bytes, None]:
        """Mock stream that fails mid-way."""
        yield b"Hello "
        yield "你好".encode('utf-8')[:2]  # Partial Chinese char
        raise ConnectionError("Stream interrupted")
    
    buffer = UTF8StreamBuffer()
    results = []
    
    try:
        async for chunk in mock_stream_with_error():
            result = buffer.process_chunk(chunk)
            if result:
                results.append(result)
    except ConnectionError:
        # Flush buffer on error
        final = buffer.flush()
        if final:
            results.append(final)
    
    reconstructed = ''.join(results)
    # Should have "Hello " and potentially replacement char for incomplete sequence
    assert "Hello" in reconstructed


@pytest.mark.asyncio
async def test_chunk_validation():
    """Test chunk validation and reassembly."""
    buffer = UTF8StreamBuffer()
    
    # Test with emoji (4-byte UTF-8 sequences)
    text = "Hello 👋 World 🌍"
    text_bytes = text.encode('utf-8')
    
    # Split emoji across chunks
    chunk1 = text_bytes[:9]   # "Hello 👋" (partial)
    chunk2 = text_bytes[9:15] # rest of "👋" + " Worl"
    chunk3 = text_bytes[15:]  # "d 🌍"
    
    result1 = buffer.process_chunk(chunk1)
    result2 = buffer.process_chunk(chunk2)
    result3 = buffer.process_chunk(chunk3)
    final = buffer.flush()
    
    reconstructed = result1 + result2 + result3 + final
    assert reconstructed == text, f"Expected '{text}', got '{reconstructed}'"


@pytest.mark.asyncio
async def test_empty_chunks():
    """Test handling of empty chunks."""
    buffer = UTF8StreamBuffer()
    
    result1 = buffer.process_chunk(b"")
    result2 = buffer.process_chunk(b"Hello")
    result3 = buffer.process_chunk(b"")
    final = buffer.flush()
    
    reconstructed = result1 + result2 + result3 + final
    assert reconstructed == "Hello"


@pytest.mark.asyncio
async def test_single_byte_chunks():
    """Test extreme case of single-byte chunks."""
    buffer = UTF8StreamBuffer()
    
    text = "你好"
    text_bytes = text.encode('utf-8')
    
    results = []
    for byte in text_bytes:
        result = buffer.process_chunk(bytes([byte]))
        if result:
            results.append(result)
    
    final = buffer.flush()
    if final:
        results.append(final)
    
    reconstructed = ''.join(results)
    assert reconstructed == text


@pytest.mark.asyncio
async def test_mixed_content_streaming():
    """Test streaming with mixed ASCII, Chinese, emoji, and special chars."""
    buffer = UTF8StreamBuffer()
    
    text = "Sales: 你好! Price: $100 💰 Discount: 20% 优惠"
    text_bytes = text.encode('utf-8')
    
    # Simulate realistic chunk sizes (10-30 bytes)
    chunk_size = 15
    chunks = [text_bytes[i:i+chunk_size] for i in range(0, len(text_bytes), chunk_size)]
    
    results = []
    for chunk in chunks:
        result = buffer.process_chunk(chunk)
        if result:
            results.append(result)
    
    final = buffer.flush()
    if final:
        results.append(final)
    
    reconstructed = ''.join(results)
    assert reconstructed == text, f"Expected '{text}', got '{reconstructed}'"


@pytest.mark.asyncio
async def test_buffer_reset():
    """Test buffer reset between streams."""
    buffer = UTF8StreamBuffer()
    
    # First stream
    text1 = "你好"
    for byte in text1.encode('utf-8'):
        buffer.process_chunk(bytes([byte]))
    buffer.flush()
    
    # Buffer should be clean for second stream
    assert buffer.incomplete_bytes == b""
    
    # Second stream
    text2 = "世界"
    result = buffer.process_chunk(text2.encode('utf-8'))
    assert result == text2
