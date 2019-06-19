from typing import Callable, Dict

from aiohttp import web, hdrs
from aiohttp.web_exceptions import HTTPClientError

from api.settings import settings


@web.middleware
async def cors_middleware(request: web.Request, handler: Callable) -> web.Response:
    cors_headers = generate_cors_headers()

    if request.method == hdrs.METH_OPTIONS:
        return web.Response(headers=cors_headers)

    try:
        response = await handler(request)
        response.headers.update(cors_headers)
        return response
    except HTTPClientError as e:
        headers = {**e.headers, **cors_headers}
        raise type(e)(reason=e.reason, text=e.text, headers=headers)


def generate_cors_headers() -> Dict:
    headers = {}

    if settings["cors"]:
        headers = {
            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: "*",
            hdrs.ACCESS_CONTROL_MAX_AGE: "600",
            hdrs.ACCESS_CONTROL_ALLOW_METHODS: ",".join([hdrs.METH_OPTIONS, hdrs.METH_GET]),
            hdrs.ACCESS_CONTROL_ALLOW_HEADERS: ",".join([hdrs.CONTENT_TYPE]),
            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS: ",".join([hdrs.CONTENT_LENGTH])
        }

    return headers
