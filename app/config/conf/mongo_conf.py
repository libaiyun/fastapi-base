import logging
from app.client.meta_service_client import MetaServiceClient
from app.db.mongo_init import init_mongo

logger = logging.getLogger(__name__)


async def get_mongo_uri() -> str:
    """从指定接口获取MongoDB URI"""
    result = await MetaServiceClient.get_app_data_version("api-search")
    return result["data"]["nowDbUrl"]


async def mongo_uri_changed(new_uri):
    """MongoDB URI变更回调函数"""
    logger.info("MongoDB URI已变更, 重新初始化连接: %s" % new_uri)
    await init_mongo(mongo_uri=new_uri)
