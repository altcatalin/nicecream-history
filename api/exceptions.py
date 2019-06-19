import json
from typing import Callable

from aiohttp import web, hdrs

from api.schemas import HTTPClientErrorSchema


@web.middleware
async def exception_middleware(request: web.Request, handler: Callable):
    try:
        response = await handler(request)
        return response
    except web.HTTPClientError as e:
        try:
            message = json.loads(e.text)
        except json.JSONDecodeError:
            message = HTTPClientErrorSchema().dump({"detail": e.text})

        headers = e.headers
        headers.pop(hdrs.CONTENT_TYPE)

        raise type(e)(reason=e.reason, text=json.dumps(message), headers=headers, content_type="application/json")
