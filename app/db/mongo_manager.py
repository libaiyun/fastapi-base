from typing import Dict, List
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


DEFAULT_ALIAS = "default"


class MongoManager:
    def __init__(self) -> None:
        self._clients: Dict[str, AsyncIOMotorClient] = {}
        self._databases: Dict[str, AsyncIOMotorDatabase] = {}

    def register(self, mongo_uri: str, db_name: str, alias: str = DEFAULT_ALIAS):
        if alias in self._clients:
            self._clients[alias].close()
        client = AsyncIOMotorClient(mongo_uri)
        self._clients[alias] = client
        self._databases[alias] = client[db_name]

    def get_client(self, alias: str = DEFAULT_ALIAS):
        return self._clients[alias]

    def get_database(self, alias: str = DEFAULT_ALIAS):
        return self._databases[alias]

    async def init_beanie(self, document_models: List[type[Document]], alias: str = DEFAULT_ALIAS):
        db = self.get_database(alias)
        await init_beanie(database=db, document_models=document_models)

    def shutdown(self):
        for client in self._clients.values():
            client.close()
        self._clients.clear()
        self._databases.clear()

    @property
    def db(self):
        return self.get_database()


# 全局唯一 mongo 管理器
mongo = MongoManager()
