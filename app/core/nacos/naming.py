import logging
import asyncio

from v2.nacos import ClientConfigBuilder, GRPCConfig, NacosNamingService
from app.config import config

# 全局变量存储单例实例和锁
_naming_service_instance = None
_lock = asyncio.Lock()


async def create_naming_service():
    global _naming_service_instance, _lock

    # 第一次检查：如果实例已存在，直接返回
    if _naming_service_instance is not None:
        return _naming_service_instance

    # 获取锁，确保只有一个协程执行初始化
    async with _lock:
        # 第二次检查：防止在等待锁时其他协程已完成初始化
        if _naming_service_instance is None:
            # 创建配置并初始化实例
            client_config = (
                ClientConfigBuilder()
                .server_address(config.nacos.server_url)
                .username(config.nacos.username)
                .password(config.nacos.password)
                .namespace_id("public")
                .grpc_config(GRPCConfig(grpc_timeout=5000))
                .log_level(logging.INFO)
                .cache_dir(str(config.nacos.cache_dir))
                .log_dir(str(config.log.log_dir))
                .build()
            )
            _naming_service_instance = await NacosNamingService.create_naming_service(client_config)

    return _naming_service_instance
