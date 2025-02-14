import asyncio
import logging
import os
from urllib.parse import urljoin

import aiohttp
import yaml

from app.utils.nacos_auth import get_token
from config import config, CACHE_CONFIG_FILE, CONFIG_FILE

logger = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=60)


class NacosConfigNotExist(Exception):
    pass


class NacosConfigSync:
    def __init__(self):
        self.config_url = urljoin(config.nacos.server_url, "/nacos/v2/cs/config")

    async def build_common_params(self):
        params = {
            "namespaceId": config.nacos.namespace_id,
            "group": config.nacos.group,
            "dataId": f"{config.service_name}.yaml",
        }
        if config.nacos.auth_enabled:
            params["accessToken"] = await get_token()
        return params

    async def fetch_config(self):
        """从 Nacos 获取配置"""
        params = await self.build_common_params()
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(self.config_url, params=params) as resp:
                try:
                    result = await resp.json()
                except Exception:
                    resp_text = await resp.text()
                    logger.error(f"API请求失败：{resp_text}")
                    raise
                # print(result)
                if result["code"] == 20004:
                    raise NacosConfigNotExist
                return result["data"]

    async def publish_config(self, content: str):
        """将配置发布到 Nacos"""
        common_params = await self.build_common_params()
        params = {
            **common_params,
            "content": content,
            "type": "yaml",
        }
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(self.config_url, data=params) as resp:
                try:
                    result = await resp.json()
                except Exception:
                    resp_text = await resp.text()
                    logger.error(f"API请求失败：{resp_text}")
                    raise
                # print(result)
                return result["data"]

    def save(self, config_content: str, cache_file: str):
        """保存配置到本地缓存文件，并进行版本备份"""
        if os.path.exists(cache_file):
            for i in range(1, 20):  # 最多保留19个历史版本
                backup_file = f"{cache_file}.{i}"
                if not os.path.exists(backup_file):
                    os.rename(cache_file, backup_file)
                    break
        with open(cache_file, "w", encoding="utf8") as f:
            f.write(config_content)

    def compare_and_save(self, cache_file: str, new_content: str) -> bool:
        """比较配置并保存"""
        new_config = yaml.safe_load(new_content)
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf8") as f:
                old_config = yaml.safe_load(f)
            if old_config == new_config:
                logger.info("配置未变更，无需保存")
                return False
        self.save(new_content, cache_file)
        return True


async def sync_nacos_config():
    """同步 Nacos 配置"""
    nacos_sync = NacosConfigSync()
    try:
        new_content = await nacos_sync.fetch_config()
        if nacos_sync.compare_and_save(CACHE_CONFIG_FILE, new_content):
            logger.info("配置已变更")
    except NacosConfigNotExist:
        logger.info("Nacos 中未找到配置，发布默认配置...")
        with open(CONFIG_FILE, "r", encoding="utf8") as f:
            default_content = f.read()
            await nacos_sync.publish_config(content=default_content)


if __name__ == "__main__":
    asyncio.run(sync_nacos_config())
