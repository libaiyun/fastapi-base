import logging
from urllib.parse import urljoin

import aiohttp

from app.utils.nacos_auth import get_token
from config import config

logger = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=60)


async def register_service():
    """服务发现注册"""
    params = {"serviceName": config.service_name, "ip": config.host, "port": config.port}
    if config.nacos.auth_enabled:
        params["accessToken"] = await get_token()
    service_register_api = "/nacos/v2/ns/instance"
    service_register_url = urljoin(config.nacos.server_url, service_register_api)
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(service_register_url, params=params) as response:
            # response.raise_for_status()
            result = await response.text()
            logger.info(f"Service registration result: {result}")
