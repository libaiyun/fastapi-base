import json
import logging
from functools import lru_cache
from typing import Sequence, List

from elasticsearch import AsyncElasticsearch

from app.exceptions import ConfigError
from config import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def get_es() -> AsyncElasticsearch:
    """
    获取ES连接对象
    """
    if config.es is None:
        raise ConfigError("ES连接未配置")
    es = AsyncElasticsearch(
        hosts=config.es.host.split(","),
        # ca_certs=ca_path,  # E:\application-service\apps\s105-c7es-01.crt
        timeout=config.es.timeout,
        verify_certs=False,
        http_auth=(config.es.user, config.es.password),
    )
    return es


async def get_by_id(eid: str, index: str):
    return await get_es().get(index=index, id=eid, request_timeout=config.es.timeout)


async def query(dsl: dict, index: str):
    """
    单条数据检索
    """
    result = await get_es().search(index=index, body=dsl, request_timeout=config.es.timeout)
    return result


async def bulk_query(dsl_list: list, index: str | Sequence[str], return_dsl=False) -> List[dict] | dict:
    """
    批量数据检索
    """
    result = []
    requests = []
    header = {"index": index}
    for dsl in dsl_list:
        # print(json.dumps(dsl, ensure_ascii=False))
        requests.extend([header, dsl])

    try:
        responses = await get_es().msearch(body=requests, index=index)
    except Exception as e:
        logger.error(f"ES批量数据检索失败: {str(e)}, index: {index}, dsl_list: {json.dumps(dsl_list)}")
        raise
    result.extend(responses["responses"])

    if return_dsl:
        return {
            "index": index,
            "dsl_list": dsl_list,
            "result": result,
        }

    return result
