from fastapi import APIRouter

from app.api.v1.routes import hero

router = APIRouter()

router.include_router(hero.router, prefix="/hero", tags=["英雄人物"])
