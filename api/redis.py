import aioredis
from aiohttp import web

from api.settings import settings


async def create_redis_connection_pool(app: web.Application) -> None:
    app['redis'] = await aioredis.create_redis_pool(settings["redis"]["url"])


async def close_redis_connection_pool(app: web.Application) -> None:
    app['redis'].close()
    await app['redis'].wait_closed()
