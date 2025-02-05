from app.api.router_base import RouterBase
from app.models.hero import Hero
from app.schemas.hero import HeroQuery, HeroCreate, HeroUpdate, HeroPublic

router = RouterBase(Hero, HeroQuery, HeroCreate, HeroUpdate, HeroPublic).get_router()
