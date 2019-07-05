import json
from typing import Callable, Dict, List, Union

from aiohttp import web
from aiohttp.web_middlewares import middleware
from marshmallow import Schema, fields, pre_dump, validate
from marshmallow.exceptions import ValidationError

from api.utils import issubclass_py37


class BaseSchema(Schema):
    @pre_dump(pass_many=True)
    def pre_dump(self, data: Union[List, Dict], many: bool):
        if many:
            return [dict(element) for element in data]

        return data


class SongSchema(BaseSchema):
    id = fields.Integer(required=True, dump_only=True)
    title = fields.Str(required=True)


class ChannelSchema(BaseSchema):
    id = fields.Integer(required=True, dump_only=True)
    name = fields.Str(required=True)
    url = fields.Str(required=True)


class ChannelExtraSchema(ChannelSchema):
    song_id = fields.Integer(required=True)
    song_title = fields.Str(required=True)


class HistoryInSchema(BaseSchema):
    song_id = fields.Integer(required=True)
    channel_id = fields.Integer(required=True)


class HistorySchema(HistoryInSchema):
    id = fields.Integer(required=True)
    created_at = fields.DateTime(required=True)
    song_title = fields.Str(required=True)


class HistoryRequestFiltersSchema(Schema):
    channel_id = fields.Integer(missing=0, default=0, validate=validate.Range(min=1))
    offset = fields.Integer(missing=0, default=0, validate=validate.Range(min=0))


class SSEMessageSchema(Schema):
    id = fields.Integer(required=True)
    event = fields.Str(required=True)
    data = fields.Nested(HistorySchema, required=True)
    retry = fields.Integer(required=True)


class UserSchema(Schema):
    sub = fields.Integer(required=True)
    picture = fields.Url(required=True)
    given_name = fields.Str(required=True)
    family_name = fields.Str(required=True)


class HTTPClientErrorSchema(Schema):
    detail = fields.Str(required=True)


class HTTPValidationErrorSchema(Schema):
    detail = fields.Dict(keys=fields.Str(), values=fields.List(fields.Dict()))


def request_validation(query_schema: Schema = None, body_schema: Schema = None) -> Callable:
    def handler_wrapper(handler: Callable) -> Callable:
        async def request_wrapper(request: web.Request, **kwargs) -> Union[Callable, web.Response]:
            errors = {}

            if query_schema:
                try:
                    query = query_schema.load(dict(request.query))
                    request["query"] = query
                except ValidationError as e:
                    errors["path"] = e.messages

            if body_schema:
                try:
                    body = body_schema.loads(await request.json())
                    request["body"] = body
                except ValidationError as e:
                    errors["body"] = e.messages

            if errors:
                validation_error_schema = HTTPValidationErrorSchema()
                data = validation_error_schema.dump({"detail": errors})
                raise web.HTTPUnprocessableEntity(text=json.dumps(data), content_type="application/json")

            return await handler(request, **kwargs)
        return request_wrapper
    return handler_wrapper
