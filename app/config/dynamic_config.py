import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DynamicConfigItem(BaseModel):
    key: str  # 配置键名，如 "mongo.uri"
    getter: Callable[[], Awaitable[Any]]  # 配置获取函数
    callback: Optional[Callable[[Any], Awaitable[None]]] = None  # 配置变更回调
    interval: int = 30  # 检查间隔(秒)


class DynamicConfigManager:
    def __init__(self) -> None:
        self.config_items: Dict[str, DynamicConfigItem] = {}
        self.current_values: Dict[str, Any] = {}
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def register(
        self,
        key: str,
        getter: Callable[[], Awaitable[Any]],
        callback: Optional[Callable[[Any], Awaitable[None]]] = None,
        interval: int = 30,
    ):
        """注册动态配置项"""
        self.config_items[key] = DynamicConfigItem(key=key, getter=getter, callback=callback, interval=interval)
        # 初始化当前值
        self.current_values[key] = await getter()
        logger.info(f"Registered dynamic config: {key}")

    async def start(self):
        """启动配置监控"""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Dynamic config manager started")

    async def stop(self):
        """停止配置监控"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Dynamic config manager stopped")

    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._check_configs()
            except Exception as e:
                logger.error(f"配置检查失败: {e}")

            # 等待最短间隔时间
            if self.config_items:
                await asyncio.sleep(min(item.interval for item in self.config_items.values()))
            else:
                await asyncio.sleep(30)

    async def _check_configs(self):
        """检查所有配置项"""
        for key, item in self.config_items.items():
            try:
                new_value = await item.getter()
                old_value = self.current_values.get(key)

                if new_value != old_value:
                    logger.info(f"配置 {key} 已变更")
                    self.current_values[key] = new_value

                    # 执行回调函数
                    if item.callback:
                        try:
                            await item.callback(new_value)
                        except Exception as e:
                            logger.error(f"配置 {key} 变更回调执行失败: {e}")
            except Exception as e:
                logger.error(f"获取配置 {key} 失败: {e}")

    def get_config(self, key: str) -> Any:
        """获取当前配置值"""
        return self.current_values[key]


# 全局实例
dynamic_config_manager = DynamicConfigManager()
