import logging
from typing import Optional, Dict, Any

from v2.nacos import NacosNamingService, ClientConfigBuilder, GRPCConfig, RegisterInstanceParam, DeregisterInstanceParam

from app.config import APP_ENV
from app.config.models import AppConfig

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    def __init__(self, config: AppConfig):
        self.config = config
        self.naming_client: Optional[NacosNamingService] = None
        self.client_config = self._build_client_config()
        self._registered = False

    def _build_client_config(self):
        """构建Nacos客户端配置"""
        return (
            ClientConfigBuilder()
            .server_address(self.config.nacos.server_url)
            .username(self.config.nacos.username)
            .password(self.config.nacos.password)
            .namespace_id("public")
            .grpc_config(GRPCConfig(grpc_timeout=5000))
            .log_level(logging.INFO)
            .cache_dir(str(self.config.nacos.cache_dir))
            .log_dir(str(self.config.log.log_dir))
            .build()
        )

    async def start(self):
        """启动服务注册"""
        if not self.config.nacos.enable_discovery:
            logger.info("服务注册功能已禁用")
            return

        try:
            # 初始化客户端
            self.naming_client = await NacosNamingService.create_naming_service(self.client_config)

            # 注册服务实例
            await self._register_instance()
            self._registered = True
            logger.info("服务实例注册成功")

        except Exception as e:
            logger.error(f"服务注册失败: {e}")
            raise

    async def stop(self):
        """停止服务注册"""
        if not self._registered or not self.naming_client:
            return

        try:
            await self._deregister_instance()
            await self.naming_client.shutdown()
            logger.info("服务实例已注销")
        except Exception as e:
            logger.error(f"服务注销失败: {e}")
            raise

    async def _register_instance(self):
        """注册服务实例"""
        register_params = RegisterInstanceParam(
            service_name=self.config.service_name,
            group_name=self.config.nacos.group,
            ip=self.config.server.host,
            port=self.config.server.port,
            weight=1.0,
            cluster_name="DEFAULT",
            metadata=self._get_metadata(),
            enabled=True,
            healthy=True,
            ephemeral=True,
        )

        await self.naming_client.register_instance(request=register_params)

    async def _deregister_instance(self):
        """注销服务实例"""
        deregister_params = DeregisterInstanceParam(
            service_name=self.config.service_name,
            group_name=self.config.nacos.group,
            ip=self.config.server.host,
            port=self.config.server.port,
            cluster_name="DEFAULT",
            ephemeral=True,
        )

        await self.naming_client.deregister_instance(request=deregister_params)

    def _get_metadata(self) -> Dict[str, Any]:
        """获取实例元数据"""
        base_metadata = {
            "environment": APP_ENV,
        }
        return base_metadata
