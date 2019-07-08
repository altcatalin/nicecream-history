import json

from aiohttp import web

from api.schemas import HTTPClientErrorSchema


async def transform_client_exception_to_json(request: web.Request, response: web.Response) -> None:
    if 400 <= response.status < 500:
        response.content_type = "application/json"

        try:
            json.loads(response.body)
        except json.JSONDecodeError:
            response.body = HTTPClientErrorSchema().dumps({"detail": response.body.decode("utf-8")}).encode("utf-8")
