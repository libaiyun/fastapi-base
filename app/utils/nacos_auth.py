from urllib.parse import urljoin

import aiohttp

from app.utils.cache import cached
from config import config


@cached(3 * 60 * 60)
async def get_token() -> str:
    auth_api = "/nacos/v1/auth/login"
    auth_url = urljoin(config.nacos.server_url, auth_api)
    auth_params = {"username": config.nacos.username, "password": config.nacos.password}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(auth_url, params=auth_params) as response:
            data = await response.json()
            return data["accessToken"]  # tokenTtl = 5*60*60
