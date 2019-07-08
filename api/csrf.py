import json
from functools import wraps
from secrets import token_urlsafe
from typing import Callable, Union

from aiohttp import web, hdrs
from aiohttp_session import get_session

from api.logger import get_logger
from api.schemas import HTTPValidationErrorSchema
from api.settings import settings

log = get_logger(__name__)


def csrf_protection(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(request: web.Request, **kwargs) -> Union[Callable,  web.Response]:
        session = await get_session(request)

        if "X-Csrf-Token" not in request.headers or request.headers["X-Csrf-Token"] != session["csrf_token"]:
            log.error("Cannot confirm anti cross-site request forgery token")
            validation_error_schema = HTTPValidationErrorSchema()
            data = validation_error_schema.dump({"detail": {"header": {"X-Csrf-Token": ["Missing or invalid value."]}}})
            raise web.HTTPUnprocessableEntity(text=json.dumps(data), content_type="application/json")

        return await handler(request, **kwargs)
    return wrapper


@web.middleware
async def csrf_middleware(request: web.Request, handler: Callable) -> web.Response:
    cookie_settings = settings["csrf"]["cookie"]
    session = await get_session(request)
    response = await handler(request)

    if "csrf_token" not in session:
        session["csrf_token"] = token_urlsafe(32)
        response.set_cookie(cookie_settings["cookie_name"],
                            value=session["csrf_token"],
                            secure=cookie_settings["secure"],
                            domain=cookie_settings["domain"],
                            httponly=False)

    return response
