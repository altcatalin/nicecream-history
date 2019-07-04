from aiohttp import web

from api.cors import cors_middleware
from api.database import create_postgres_connection_pool, close_postgres_connection_pool
from api.exceptions import exception_middleware
from api.logger import setup_logging
from api.openapi import generate_openapi_spec, get_openapi_handler
from api.redis import create_redis_connection_pool, close_redis_connection_pool
from api.schemas import request_path_validation_middleware
from api.settings import settings
from api.sse import create_sse_redis_subscriber, cancel_sse_redis_subscriber, close_sse_streams
from api.views import get_channels_handler, get_history_handler, get_history_events_handler


async def build() -> web.Application:
    setup_logging()

    app = web.Application()
    app["settings"] = settings

    openapi_route_url = app["settings"]["openapi"]["route"]["url"]
    openapi_route_name = app["settings"]["openapi"]["route"]["name"]

    app.router.add_get("/channels", get_channels_handler, name="channels")
    app.router.add_get("/history", get_history_handler, name="history")
    app.router.add_get("/history/events", get_history_events_handler, name="history_events")
    app.router.add_get(openapi_route_url, get_openapi_handler, name=openapi_route_name)

    app.middlewares.append(exception_middleware)
    app.middlewares.append(cors_middleware)
    app.middlewares.append(request_path_validation_middleware)

    app.on_startup.append(create_postgres_connection_pool)
    app.on_startup.append(create_redis_connection_pool)
    app.on_startup.append(create_sse_redis_subscriber)
    app.on_startup.append(generate_openapi_spec)

    app.on_shutdown.append(close_sse_streams)

    app.on_cleanup.append(cancel_sse_redis_subscriber)
    app.on_cleanup.append(close_redis_connection_pool)
    app.on_cleanup.append(close_postgres_connection_pool)

    return app


def main() -> None:
    app = build()
    web.run_app(app, host=settings["server"]["host"], port=settings["server"]["port"])


if __name__ == '__main__':
    main()
