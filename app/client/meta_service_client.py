from app.core.nacos.discovery import service_discovery
from app.utils.api_util import APIUtil


class _MetaServiceClient:
    """MetaService API客户端"""

    def __init__(self, service_name: str = "api-meta-service") -> None:
        self.service_name = service_name

    async def _get_base_url(self) -> str:
        """获取服务实例的基础 URL"""
        instance = await service_discovery.select_instance(self.service_name)
        return f"http://{instance.ip}:{instance.port}"

    async def get_app_data_version(self, target_service_name: str):
        """
        调用 /meta-service/v1/version/appDataVersion 接口
        :param target_service_name: 目标服务名，例如 "api-search"
        :return: 接口返回的 JSON 数据
        """
        base_url = await self._get_base_url()
        api_path = "/meta-service/v1/version/appDataVersion"
        url = f"{base_url}{api_path}"
        payload = {"serviceName": target_service_name}
        result = await APIUtil.fetch_post(url, payload)
        return result


MetaServiceClient = _MetaServiceClient()
