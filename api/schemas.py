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
    detail = fields.Dict(keys=fields.Str(), values=fields.List(fields.Str()))


def request_path_schema(schema: Schema) -> Callable:
    def wrapper(handler) -> Callable:
        if not hasattr(handler, "__path_schema__"):
            handler.__path_schema__ = schema
        return handler
    return wrapper


@middleware
async def request_path_validation_middleware(request: web.Request, handler: Callable) -> web.Response:
    request_handler = request.match_info.handler

    if not hasattr(request_handler, "__path_schema__"):
        if not issubclass_py37(request_handler, web.View):
            return await handler(request)

        class_handler = getattr(request_handler, request.method.lower(), None)

        if class_handler is None or not hasattr(class_handler, "__path_schema__"):
            return await handler(request)

        schema = class_handler.__path_schema__
    else:
        schema = request_handler.__path_schema__

    try:
        parameters = schema.load(dict(request.query))
        request["parameters"] = parameters
    except ValidationError as e:
        validation_error_schema = HTTPValidationErrorSchema()
        validation_errors = validation_error_schema.dump({"detail": e.messages})
        raise web.HTTPUnprocessableEntity(text=json.dumps(validation_errors), content_type="application/json")

    response = await handler(request)
    return response
