import aiohttp
import logging
from urllib.parse import urljoin
from typing import Optional

from config.models import NacosConfig

logger = logging.getLogger(__name__)


class NacosConfigNotExist(Exception):
    pass


class NacosClient:
    def __init__(self, nacos_config: NacosConfig, service_name: str):
        self.nacos_config = nacos_config
        self.service_name = service_name
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc_info):
        await self.close()

    async def connect(self):
        """创建连接会话"""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        if self.nacos_config.auth_enabled:
            self._token = await self._get_access_token()

    async def close(self):
        """关闭会话"""
        if self._session:
            await self._session.close()

    async def _get_access_token(self):
        """获取访问令牌"""
        auth_url = urljoin(self.nacos_config.server_url, "/nacos/v1/auth/login")
        params = {"username": self.nacos_config.username, "password": self.nacos_config.password}
        async with self._session.post(auth_url, params=params) as resp:
            data = await resp.json()
            return data["accessToken"]  # tokenTtl = 5*60*60

    async def fetch_config(self) -> str:
        """获取配置"""
        params = {
            "namespaceId": self.nacos_config.namespace_id,
            "group": self.nacos_config.group,
            "dataId": f"{self.service_name}.yaml",
        }
        if self.nacos_config.auth_enabled:
            params["accessToken"] = self._token

        url = urljoin(self.nacos_config.server_url, "/nacos/v2/cs/config")
        async with self._session.get(url, params=params) as resp:
            # resp.raise_for_status()
            try:
                result = await resp.json()
                # print(result)
                if result["code"] == 20004:
                    raise NacosConfigNotExist
                return result["data"]
            except Exception:
                logger.error(f"API请求失败：{(await resp.text())}")
                raise

    async def publish_config(self, content: str) -> bool:
        """发布配置"""
        params = {
            "namespaceId": self.nacos_config.namespace_id,
            "group": self.nacos_config.group,
            "dataId": f"{self.service_name}.yaml",
            "content": content,
            "type": "yaml",
        }
        if self.nacos_config.auth_enabled:
            params["accessToken"] = self._token

        url = urljoin(self.nacos_config.server_url, "/nacos/v2/cs/config")
        async with self._session.post(url, data=params) as resp:
            try:
                result = await resp.json()
                # print(result)
                return result["data"]
            except Exception:
                resp_text = await resp.text()
                logger.error(f"API请求失败：{resp_text}")
                raise
