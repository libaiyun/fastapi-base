import asyncio
import logging
import os

import aiohttp
import yaml

from config import config, CACHE_CONFIG_FILE, CONFIG_FILE

logger = logging.getLogger("scheduler_async")
TIMEOUT = aiohttp.ClientTimeout(total=60)


class NacosConfigNotExist(Exception):
    pass


class NacosConfigSync:
    def __init__(self, server_address: str, namespace: str, data_id: str, group: str):
        self.server_address = server_address
        self.namespace = namespace
        self.data_id = data_id
        self.group = group

    async def fetch_config(self):
        """从 Nacos 获取配置"""
        api = "/nacos/v2/cs/config"
        params = {
            "namespaceId": self.namespace,
            "group": self.group,
            "dataId": self.data_id,
        }
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(self.server_address + api, params=params) as resp:
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
        api = "/nacos/v2/cs/config"
        params = {
            "namespaceId": self.namespace,
            "group": self.group,
            "dataId": self.data_id,
            "content": content,
            "type": "yaml",
        }
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(self.server_address + api, data=params) as resp:
                try:
                    result = await resp.json()
                except Exception:
                    resp_text = await resp.text()
                    logger.error(f"API请求失败：{resp_text}")
                    raise
                # print(result)
                return result["data"]

    @staticmethod
    def save_to_local(config_content: str, cache_file: str):
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
        self.save_to_local(new_content, cache_file)
        return True


async def sync_nacos_config():
    """同步 Nacos 配置"""
    nacos_sync = NacosConfigSync(
        server_address=config.nacos.server_address,
        namespace=config.nacos.namespace,
        data_id=config.nacos.data_id,
        group=config.nacos.group,
    )
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
    import logging.config
    from app.core.log import LOGGING_CONFIG

    logging.config.dictConfig(LOGGING_CONFIG)
    asyncio.run(sync_nacos_config())
