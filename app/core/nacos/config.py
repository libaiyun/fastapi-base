import logging
from typing import Optional

import yaml
from v2.nacos import NacosConfigService, ClientConfigBuilder, GRPCConfig, ConfigParam

from app.config import AppConfig, config

logger = logging.getLogger(__name__)


class ConfigSyncer:
    def __init__(self, _config: AppConfig):
        self.config = _config
        self.config_client: Optional[NacosConfigService] = None
        self.client_config = self._build_client_config()
        self._data_id = f"{_config.service_name}.yaml"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()

    def _build_client_config(self):
        """构建Nacos客户端配置"""
        return (
            ClientConfigBuilder()
            .server_address(self.config.nacos.server_url)
            .username(self.config.nacos.username)
            .password(self.config.nacos.password)
            .namespace_id(self.config.nacos.namespace_id)
            .grpc_config(GRPCConfig(grpc_timeout=5000))
            .log_level(logging.INFO)
            .cache_dir(str(self.config.nacos.cache_dir))
            .log_dir(str(self.config.log.log_dir))
            .build()
        )

    async def start(self):
        """启动配置同步服务"""
        if self.config.nacos.enable_config is False:  # 是否启用配置同步
            return

        try:
            # 初始化客户端
            self.config_client = await NacosConfigService.create_config_service(self.client_config)

            # 首次配置检查与发布
            await self._initial_config_check()

            # 注册监听器
            await self.config_client.add_listener(self._data_id, self.config.nacos.group, self._config_listener)
        except Exception as e:
            logger.error(f"Nacos配置服务初始化失败: {e}")
            raise

    async def stop(self):
        """停止配置同步服务"""
        if self.config_client:
            await self.config_client.remove_listener(self._data_id, self.config.nacos.group, self._config_listener)
            await self.config_client.shutdown()
            logger.info("Nacos配置同步已停止")

    async def _initial_config_check(self):
        """初始配置检查与发布"""
        param = ConfigParam(
            data_id=self._data_id,
            group=self.config.nacos.group,
        )

        try:
            content = await self.config_client.get_config(param)
            if not content:
                await self._publish_default_config()
                logger.info("初始配置发布成功")
            else:
                self._update_local_config(content)
                logger.info("成功加载远程配置")
        except Exception as e:
            logger.error(f"初始配置检查失败: {e}")
            raise

    async def _publish_default_config(self):
        """发布默认配置"""
        config_content = yaml.dump(self.config.model_dump(include={"project_name"}), sort_keys=False)

        param = ConfigParam(
            data_id=self._data_id,
            group=self.config.nacos.group,
            content=config_content,
            type="yaml",
        )

        try:
            await self.config_client.publish_config(param)
        except Exception as e:
            logger.error(f"默认配置发布失败: {e}")
            raise

    def _update_local_config(self, content: str):
        """更新本地配置"""
        try:
            new_config = yaml.safe_load(content)
            self.config.__init__(**new_config)
        except Exception as e:
            logger.error(f"配置解析失败: {e}")
            raise

    async def _config_listener(self, tenant: str, data_id: str, group: str, content: Optional[str]):
        """配置变更监听回调"""
        try:
            if content is None:
                logger.warning("监听到配置删除，尝试重新发布默认配置...")
                await self._publish_default_config()
            else:
                self._update_local_config(content)
                logger.info("配置变更已生效")
        except Exception as e:
            logger.error(f"配置监听处理失败: {e}")


config_syncer = ConfigSyncer(config)
