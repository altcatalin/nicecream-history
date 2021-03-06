from pathlib import Path

import aiohttp_jinja2
import aiohttp_session
import jinja2
from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from api.cors import cors_middleware, set_cors
from api.csrf import csrf_middleware
from api.database import create_postgres_connection_pool, close_postgres_connection_pool
from api.exception import transform_client_exception_to_json
from api.logger import setup_logging
from api.openapi import generate_openapi_spec, get_openapi_handler
from api.redis import create_redis_connection_pool, close_redis_connection_pool
from api.settings import settings
from api.sse import create_sse_redis_subscriber, cancel_sse_redis_subscriber, close_sse_streams
from api.swagger import get_swagger_ui_handler
from api.views import *


async def build() -> web.Application:
    setup_logging()

    cookie_storage = EncryptedCookieStorage(**settings["session"]["cookie"])
    openapi_route = settings["openapi"]["route"]

    app = web.Application()
    app["settings"] = settings

    current_path = Path(__file__).resolve().parent
    templates_path = str(current_path.joinpath('templates'))
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(templates_path))

    app.router.add_get("/", get_swagger_ui_handler, name="swagger")
    app.router.add_get("/channels", get_channels_handler, name="channels")
    app.router.add_get("/history", get_history_handler, name="history")
    app.router.add_get("/history/events", get_history_events_handler, name="history_events")
    app.router.add_get("/user", get_user_handler, name="user")
    app.router.add_get("/user/sign_out", get_user_sign_out_handler, name="user_sign_out")
    app.router.add_get("/user/google", get_user_google_handler, name="user_google")
    app.router.add_get("/user/google/callback", get_user_google_callback_handler, name="user_google_callback")
    app.router.add_get("/user/bookmarks", get_user_bookmarks_handler, name="user_bookmarks")
    app.router.add_post("/user/bookmarks", post_user_bookmarks_handler, name="post_user_bookmarks")
    app.router.add_delete("/user/bookmarks/{bookmark_id}", delete_user_bookmarks_handler, name="delete_user_bookmarks")
    app.router.add_get(openapi_route["url"], get_openapi_handler, name=openapi_route["name"])

    app.middlewares.append(aiohttp_session.session_middleware(cookie_storage))
    app.middlewares.append(cors_middleware)
    app.middlewares.append(csrf_middleware)

    app.on_response_prepare.append(set_cors)
    app.on_response_prepare.append(transform_client_exception_to_json)

    app.on_startup.append(create_postgres_connection_pool)
    app.on_startup.append(create_redis_connection_pool)
    app.on_startup.append(create_sse_redis_subscriber)
    app.on_startup.append(generate_openapi_spec)

    app.on_shutdown.append(close_sse_streams)

    app.on_cleanup.append(cancel_sse_redis_subscriber)
    app.on_cleanup.append(close_redis_connection_pool)
    app.on_cleanup.append(close_postgres_connection_pool)

    return app

