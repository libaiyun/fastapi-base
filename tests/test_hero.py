import pytest

from app.crud.base import CRUDBase
from app.models.hero import Hero
from app.schemas.query import CommonQuery, Condition, Operator
from app.service.base import BaseService


@pytest.mark.asyncio
async def test_api(client):
    params = {"name": "n1", "secret_name": "s1", "intro": "i1", "address_info": {}}
    result = await client.post("/api/v1/hero/create", json=params)
    assert result.status_code == 200
    data = result.json()["data"]
    assert data["id"]
    assert data["name"] == "n1"

    result = await client.get("/api/v1/hero/list?name=n1&count=true")
    assert result.json()["data"]["items"][0]["name"] == "n1"


@pytest.mark.asyncio
async def test_service(db_session):
    service = BaseService[Hero](Hero)
    await service.create(db_session, Hero(name="n1", secret_name="s1", intro="i1", address_info={}))
    data = await service.list(db_session, CommonQuery(fields="id,name"))
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_crud(db_session):
    crud = CRUDBase[Hero](Hero)
    await crud.create(db_session, Hero(name="n1", secret_name="s1", intro="i1", address_info={}))
    db_item = await crud.get_first(db_session, condition=Condition(field="name", operator=Operator.EQ, value="n1"))
    assert db_item.intro == "i1"
