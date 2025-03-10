import asyncio
import logging
from typing import Optional

import yaml

from config.models import AppConfig
from config.nacos_client import NacosClient, NacosConfigNotExist

logger = logging.getLogger(__name__)


class ConfigSyncer:
    def __init__(self, config: AppConfig):
        self.config = config
        self._sync_task: Optional[asyncio.Task] = None

    def start(self):
        """启动配置同步"""
        if self._should_sync():
            self._sync_task = asyncio.create_task(self._sync_loop())

    async def stop(self):
        """停止配置同步"""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

    def _should_sync(self):
        return self.config.nacos and self.config.nacos.enable_config_sync and self.config.nacos.sync_interval > 0

    async def _sync_loop(self):
        """配置同步循环"""
        while True:
            try:
                await self.sync_from_nacos()
                await asyncio.sleep(self.config.nacos.sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"配置同步失败，将在30秒后重试。错误: {e}")
                await asyncio.sleep(30)

    async def sync_from_nacos(self):
        """从Nacos同步配置"""
        async with NacosClient(self.config.nacos, self.config.service_name) as client:
            try:
                # logger.info("正在从Nacos同步配置...")
                content = await client.fetch_config()
                self.config.__init__(**yaml.safe_load(content))
                logger.info("配置同步成功")
            except NacosConfigNotExist:
                logger.info("Nacos配置不存在, 正在发布默认配置...")
                # content = yaml.dump(self.config.model_dump(mode="json"), sort_keys=False)
                data = await client.publish_config(yaml.dump(self.config.model_dump(include={"project_name"})))
                logger.info(f"配置发布成功: {data}")
