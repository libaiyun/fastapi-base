import logging
from typing import Optional

from app.config import config
from app.db.mongo_manager import mongo
from app.models import odm_models

logger = logging.getLogger(__name__)


async def init_mongo(mongo_uri: Optional[str] = None):
    """初始化 MongoDB 连接 & Beanie 模型"""
    if mongo_uri is None:
        mongo_uri = config.mongo.uri
    db_name = config.mongo.db
    mongo.register(mongo_uri=mongo_uri, db_name=db_name)
    await mongo.init_beanie(document_models=odm_models)
    logger.info("MongoDB 初始化完成: %s / %s", mongo_uri, db_name)


def close_mongo():
    """关闭 MongoDB 连接"""
    mongo.shutdown()
    logger.info("MongoDB 连接已关闭")
