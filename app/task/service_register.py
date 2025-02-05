import logging

import aiohttp

from config import config

logger = logging.getLogger(__name__)


async def register_service():
    params = {"ip": config.host, "port": config.port}
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(config.gateway.service_register_url, params=params) as response:
            # response.raise_for_status()
            result = await response.text()
            logger.info(f"Service registration result: {result}")
