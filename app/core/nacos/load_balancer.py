import asyncio
from abc import ABC, abstractmethod
from typing import List

from v2.nacos import Instance


class LoadBalancer(ABC):
    @abstractmethod
    async def select(self, service_name: str, instances: List[Instance]) -> Instance:
        """选择下一个实例"""

    @abstractmethod
    async def reset(self, service_name: str):
        """重置特定服务的索引"""


class RoundRobinBalancer(LoadBalancer):
    def __init__(self):
        self._indexes = {}  # 服务名 -> 当前索引
        self._lock = asyncio.Lock()

    async def select(self, full_service_name: str, instances: List[Instance]) -> Instance:
        if not instances:
            raise ValueError("No available instances")

        async with self._lock:
            index = self._indexes.get(full_service_name, 0)
            selected = instances[index % len(instances)]
            self._indexes[full_service_name] = index + 1
            return selected

    async def reset(self, full_service_name: str):
        async with self._lock:
            if full_service_name in self._indexes:
                self._indexes[full_service_name] = 0
