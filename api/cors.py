from typing import Callable, Dict

from aiohttp import web, hdrs
from aiohttp.web_exceptions import HTTPClientError

from api.settings import settings


async def set_cors(request: web.Request, response: web.Response) -> None:
    cors_headers = generate_cors_headers()
    for name, value in cors_headers.items():
        response.headers[name] = value


@web.middleware
async def cors_middleware(request: web.Request, handler: Callable) -> web.Response:
    if request.method == hdrs.METH_OPTIONS:
        cors_headers = generate_cors_headers()
        return web.Response(headers=cors_headers)

    response = await handler(request)
    return response


def generate_cors_headers() -> Dict:
    headers = {}
    allowed_methods = [hdrs.METH_OPTIONS, hdrs.METH_GET, hdrs.METH_POST, hdrs.METH_DELETE, hdrs.METH_PUT, hdrs.METH_PATCH]
    allowed_headers = [hdrs.CONTENT_TYPE] + settings["cors"]["headers"].split(",")

    if settings["cors"]["allowed"]:
        headers = {
            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: settings["cors"]["origin"],
            hdrs.ACCESS_CONTROL_MAX_AGE: "600",
            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS: "true",
            hdrs.ACCESS_CONTROL_ALLOW_METHODS: ",".join(allowed_methods),
            hdrs.ACCESS_CONTROL_ALLOW_HEADERS: ",".join(allowed_headers),
            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS: ",".join([hdrs.CONTENT_LENGTH])
        }

    return headers
