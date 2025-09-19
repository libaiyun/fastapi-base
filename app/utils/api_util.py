import logging
import aiohttp
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class _APIUtil:
    def __init__(self, timeout=30) -> None:
        self.timeout = timeout
        self._session = None

    def get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout))
        return self._session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=True,
    )
    async def fetch_post(self, url, payload):
        async with self.get_session().post(url, json=payload) as response:
            try:
                response.raise_for_status()
                result = await response.json()
                return result
            except aiohttp.ClientError as e:
                # 打印返回的文本内容
                text = await response.text()
                logger.warning(
                    "POST %s 请求失败 [status=%s], response=%s, payload=%s, error=%s",
                    url,
                    response.status,
                    text,
                    payload,
                    repr(e),
                )
                raise


APIUtil = _APIUtil()
