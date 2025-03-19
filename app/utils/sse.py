import codecs
import logging
from typing import Optional, AsyncGenerator, AsyncIterator

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ServerSentEvent(BaseModel):
    data: str
    event: str = "message"
    id: Optional[str] = None
    retry: Optional[int] = None

    def __str__(self):
        lines = []
        # 处理 data 字段，按换行符分割并添加前缀
        for line in self.data.split("\n"):
            lines.append(f"data: {line}")
        # 添加 event 字段
        lines.append(f"event: {self.event}")
        # 处理 id 字段（若存在）
        if self.id is not None:
            lines.append(f"id: {self.id}")
        # 处理 retry 字段（若存在）
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        # 合并所有行并以双换行符结尾
        return "\n".join(lines) + "\n\n"


class SSEDecoder:
    def __init__(
        self,
        stream: AsyncIterator[bytes],
        *,
        max_buffer_size: int = 1024 * 1024,  # 1MB
        encoding: str = "utf-8",
        errors: str = "replace",
    ):
        self.stream = stream
        self.max_buffer_size = max_buffer_size
        # self.encoding = encoding
        # self.errors = errors
        self._bytes_buffer = b""
        self._text_buffer = ""
        # 创建增量解码器实例
        self._decoder = codecs.getincrementaldecoder(encoding)(errors=errors)

    async def _read_chunk(self) -> None:
        try:
            chunk = await anext(self.stream)
            if len(self._bytes_buffer) + len(chunk) > self.max_buffer_size:
                raise BufferError("SSE buffer overflow")
            self._bytes_buffer += chunk
        except StopAsyncIteration:
            pass

    # def _decode_bytes(self) -> None:
    #     try:
    #         decoded = self._bytes_buffer.decode(self.encoding, errors=self.errors)
    #         self._text_buffer += decoded.replace('\r\n', '\n').replace('\r', '\n')  # 统一换行符
    #         self._bytes_buffer = b""
    #     except UnicodeDecodeError as e:
    #         # 处理不完整字节序列的特殊情况
    #         if e.reason == "unexpected end of data":
    #             # 保留未解码的尾部字节
    #             cut_point = e.start
    #             decoded = self._bytes_buffer[:cut_point].decode(self.encoding, errors=self.errors)
    #             self._text_buffer += decoded.replace('\r\n', '\n').replace('\r', '\n')  # 统一换行符
    #             self._bytes_buffer = self._bytes_buffer[cut_point:]
    #         else:
    #             raise
    def _decode_bytes(self) -> None:
        """将字节缓冲区内容解码为文本"""
        # 将缓冲区的字节数据传递给解码器
        decoded = self._decoder.decode(self._bytes_buffer)
        self._text_buffer += decoded.replace("\r\n", "\n").replace("\r", "\n")  # 统一换行符
        # 清空字节缓冲区，解码器内部会自行管理未完成字节
        self._bytes_buffer = b""

    def _finalize_decode(self) -> None:
        """处理流结束时的剩余字节"""
        # 最终解码并清空解码器内部缓冲区
        final_decoded = self._decoder.decode(b"", final=True)
        self._text_buffer += final_decoded.replace("\r\n", "\n").replace("\r", "\n")  # 统一换行符

    def _parse_event(self, event_str: str) -> ServerSentEvent:
        event_data = {"data": []}

        # 处理不同换行格式并保留有效行
        lines = []
        for raw_line in event_str.splitlines():
            line = raw_line.lstrip()
            if not line or line.startswith(":"):  # 跳过空行和注释
                continue
            lines.append(line)

        for line in lines:
            # 处理字段分割
            if ":" in line:
                field, value = line.split(":", 1)
                field = field.strip().lower()  # 规范要求字段名大小写不敏感
                # 仅删除第一个前导空格（如果存在）
                value = value[1:] if (value and value[0] == " ") else value
            else:
                field = line.lower()
                value = ""

            # 字段处理逻辑
            if field == "data":
                event_data["data"].append(value)
            elif field in ("event", "id"):
                event_data[field] = value
            elif field == "retry":
                try:
                    # 限制最小重试时间
                    event_data["retry"] = max(int(value), 100)
                except ValueError:
                    pass

        # 合并数据时保留原始换行语义
        event_data["data"] = "\n".join(event_data["data"])

        try:
            return ServerSentEvent(**event_data)
        except ValidationError as e:
            logger.error(f"SSE Validation failed: {e}\nRaw event: {event_str}")
            return ServerSentEvent(data=event_str)

    async def events(self) -> AsyncGenerator[ServerSentEvent, None]:
        while True:
            # 优先处理缓冲区中的完整事件
            while "\n\n" in self._text_buffer:
                event_part, self._text_buffer = self._text_buffer.split("\n\n", 1)
                yield self._parse_event(event_part)

            # 读取新数据
            await self._read_chunk()
            if not self._bytes_buffer:
                self._finalize_decode()
                while "\n\n" in self._text_buffer:
                    _event_part, self._text_buffer = self._text_buffer.split("\n\n", 1)
                    yield self._parse_event(_event_part)
                if self._text_buffer:
                    yield self._parse_event(self._text_buffer)
                    self._text_buffer = ""
                break

            # 尝试解码新数据
            self._decode_bytes()
