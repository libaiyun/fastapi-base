import asyncio
import logging
from urllib.parse import urljoin

import aiohttp

from app.utils.nacos_auth import get_token
from config import config

logger = logging.getLogger(__name__)


async def register_service():
    """服务发现注册"""
    params = {
        "serviceName": config.service_name,
        "ip": config.server.host,
        "port": config.server.port,
        "ephemeral": "true",
    }
    if config.nacos.auth_enabled:
        params["accessToken"] = await get_token()
    service_register_api = "/nacos/v2/ns/instance"
    service_register_url = urljoin(config.nacos.server_url, service_register_api)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(service_register_url, params=params) as response:
            # response.raise_for_status()
            result = await response.text()
            logger.info(f"Service registration result: {result}")


async def periodic_register(interval: int = 10):
    """定时服务注册"""
    while True:
        if not config.nacos.enable_service_register:
            await asyncio.sleep(30)
            continue
        try:
            await register_service()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Service registration failed: {e}", exc_info=True)
        await asyncio.sleep(interval)
