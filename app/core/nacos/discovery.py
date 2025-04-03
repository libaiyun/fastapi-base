import logging
from typing import Dict, List, Optional

from v2.nacos import (
    NacosNamingService,
    ListInstanceParam,
    Instance,
    SubscribeServiceParam,
)
from v2.nacos.naming.util.naming_client_util import get_group_name

from app.core.nacos.load_balancer import RoundRobinBalancer
from app.core.nacos.naming import create_naming_service
from app.exceptions import NoInstanceAvailable, RemoteServiceException

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """Nacos服务发现核心类，实现服务注册发现、实例缓存、动态更新等功能

    特性：
    - 自动维护实例缓存
    - 支持服务变更订阅
    - 内置轮询负载均衡
    """

    def __init__(self):
        self.naming_client: Optional[NacosNamingService] = None
        self.instance_cache: Dict[str, List[Instance]] = {}
        self.balancer = RoundRobinBalancer()
        self._subscribed_services = set()  # 跟踪已订阅的服务

    async def init(self):
        """初始化Nacos客户端连接"""
        try:
            logger.info("Initializing Nacos client...")
            self.naming_client = await create_naming_service()
            logger.info("Nacos client initialized successfully")
        except Exception as e:
            raise RemoteServiceException("Nacos client init failed") from e

    async def get_instances(self, service_name: str, group: str = "DEFAULT_GROUP") -> List[Instance]:
        """获取服务实例列表（带缓存机制）"""
        cache_key = get_group_name(service_name, group)
        logger.debug(f"Getting instances for [{cache_key}]")

        try:
            await self.subscribe_service(service_name, group)
            # 优先使用缓存
            if cache_key in self.instance_cache:
                return self.instance_cache[cache_key]
            # 从Nacos获取最新实例
            instances = await self._fetch_instances(service_name, group)
            logger.info(f"Initial instance list updated for [{cache_key}], count: {len(instances)}")
            self.instance_cache[cache_key] = instances
            return instances
        except Exception as e:
            logger.error(f"Failed to get instances for [{cache_key}]: {e}", exc_info=True)
            raise

    async def _fetch_instances(self, service_name: str, group: str) -> List[Instance]:
        """从Nacos获取实时实例列表"""
        logger.debug(f"Fetching fresh instances from Nacos for [{group}@@{service_name}]")
        try:
            param = ListInstanceParam(
                service_name=service_name,
                group_name=group,
                subscribe=True,
                healthy_only=True,
            )
            return await self.naming_client.list_instances(param)
        except Exception as e:
            logger.error(f"获取实例失败: {e}", exc_info=True)
            return self.instance_cache.get(get_group_name(service_name, group), [])

    async def select_instance(self, service_name: str, group: str = "DEFAULT_GROUP") -> Instance:
        """选择服务实例"""
        logger.debug(f"Selecting instance for [{group}@@{service_name}]")
        instances = await self.get_instances(service_name, group)
        if not instances:
            raise NoInstanceAvailable(f"服务 [{group}]{service_name} 无可用实例")
        return await self.balancer.select(service_name, instances)

    async def on_instances_changed(self, service_name: str, group: str, new_instances: List[Instance]):
        """实例更新回调"""
        cache_key = get_group_name(service_name, group)
        logger.info(f"Processing instance change for [{cache_key}], new count: {len(new_instances)}")
        self.instance_cache[cache_key] = new_instances
        await self.balancer.reset(cache_key)  # 重置索引保证有效性

    async def subscribe_service(self, service_name: str, group: str = "DEFAULT_GROUP"):
        """订阅服务变更（幂等操作）"""
        cache_key = get_group_name(service_name, group)

        async def update_callback(instances: list[Instance]):
            logger.info(f"服务 [{group}]{service_name} 实例更新, 新实例列表: {[i.ip for i in instances]}")
            try:
                await self.on_instances_changed(service_name, group, new_instances=instances)
            except Exception as e:
                logger.error(f"处理实例更新失败: {e}", exc_info=True)

        if cache_key in self._subscribed_services:
            logger.debug(f"Already subscribed to [{cache_key}]")
            return
        self._subscribed_services.add(cache_key)

        logger.info(f"Subscribing to service [{cache_key}]")
        param = SubscribeServiceParam(
            service_name=service_name,
            group_name=group,
            subscribe_callback=update_callback,
        )
        await self.naming_client.subscribe(param)
        logger.info(f"Successfully subscribed to [{cache_key}]")

    async def shutdown(self):
        """关闭客户端并清理资源"""
        if self.naming_client:
            logger.info("Shutting down Nacos client...")
            try:
                await self.naming_client.shutdown()
                logger.info("Nacos client shutdown completed")
            except Exception as e:
                logger.error(f"Error during client shutdown: {str(e)}", exc_info=True)
            finally:
                self.naming_client = None


service_discovery = ServiceDiscovery()
