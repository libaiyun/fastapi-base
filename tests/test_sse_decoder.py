import pytest
from app.utils.sse import SSEDecoder


@pytest.mark.asyncio
async def test_single_event():
    """基本事件解析"""

    async def stream():
        yield b"data: hello\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert len(events) == 1
    assert events[0].data == "hello"


@pytest.mark.asyncio
async def test_chunked_data():
    """分块数据传输"""

    async def stream():
        yield b"data: he"
        yield b"llo\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "hello"


@pytest.mark.asyncio
async def test_multiple_events():
    """多事件处理"""

    async def stream():
        yield b"data: first\n\ndata: second\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert [e.data for e in events] == ["first", "second"]


@pytest.mark.asyncio
async def test_crlf_newlines():
    """不同换行符处理"""

    async def stream():
        yield b"data: test\r\n\r\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "test"


@pytest.mark.asyncio
async def test_mixed_newlines():
    """不同换行符处理"""

    async def stream():
        yield b"data: line1\r\ndata: line2\n\r\n\ndata: next\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert [e.data for e in events] == ["line1\nline2", "next"]


@pytest.mark.asyncio
async def test_buffer_overflow():
    """缓冲区溢出保护"""

    async def stream():
        yield b"x" * (1024 * 1024 + 1)

    decoder = SSEDecoder(stream(), max_buffer_size=1024 * 1024)
    with pytest.raises(BufferError):
        async for _ in decoder.events():
            pass


@pytest.mark.asyncio
async def test_invalid_utf8():
    """编码错误处理"""

    async def stream():
        yield b"data: \x80\n\n"

    decoder = SSEDecoder(stream(), errors="replace")
    events = [event async for event in decoder.events()]
    assert events[0].data == "�"


@pytest.mark.asyncio
async def test_case_insensitive_field():
    """字段名大小写不敏感"""

    async def stream():
        yield b"Data: hello\nEvent: test\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "hello"
    assert events[0].event == "test"


@pytest.mark.asyncio
async def test_field_value_space():
    """字段值格式处理"""

    async def stream():
        yield b"data:   value\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "  value"


@pytest.mark.asyncio
async def test_retry_parsing():
    """重试逻辑验证"""

    async def stream():
        yield b"retry: 50\n\n"
        yield b"retry: invalid\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].retry == 100
    assert events[1].retry is None


@pytest.mark.asyncio
async def test_incomplete_final_event():
    """不完整事件处理"""

    async def stream():
        yield b"data: incomplete"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "incomplete"


@pytest.mark.asyncio
async def test_ignore_comments_and_blanks():
    """注释和空行跳过"""

    async def stream():
        yield b":comment\ndata: test\n\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "test"


@pytest.mark.asyncio
async def test_event_id_and_type():
    async def stream():
        yield b"id: 123\nevent: error\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].id == "123"
    assert events[0].event == "error"


@pytest.mark.asyncio
async def test_multiline_data():
    """多行数据处理"""

    async def stream():
        yield b"data: line1\ndata: line2\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "line1\nline2"


@pytest.mark.asyncio
async def test_complex_event():
    """复杂事件结构"""

    async def stream():
        yield b"event: update\ndata: new data\nid: abc\nretry: 2000\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].dict() == {"data": "new data", "event": "update", "id": "abc", "retry": 2000}


@pytest.mark.asyncio
async def test_unicode_characters():
    """Unicode字符支持"""

    async def stream():
        yield "data: 你好\n\n".encode("utf-8")

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == "你好"


@pytest.mark.asyncio
async def test_empty_data_field():
    """空数据字段处理"""

    async def stream():
        yield b"data:\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].data == ""


@pytest.mark.asyncio
async def test_multiple_retry_attempts():
    """多次字段覆盖"""

    async def stream():
        yield b"retry: 1500\nretry: 2000\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].retry == 2000  # Last value should win


@pytest.mark.asyncio
async def test_partial_field_parsing():
    """分块字段解析"""

    async def stream():
        yield b"event:stream"
        yield b"-start\ndata: loaded\n\n"

    decoder = SSEDecoder(stream())
    events = [event async for event in decoder.events()]
    assert events[0].event == "stream-start"
    assert events[0].data == "loaded"
