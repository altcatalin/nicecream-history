import json
from functools import wraps
from json import JSONDecodeError
from typing import Callable, Dict, List, Union

from aiohttp import web
from marshmallow import Schema, fields, pre_dump, validate
from marshmallow.exceptions import ValidationError


class BaseSchema(Schema):
    @pre_dump(pass_many=True)
    def pre_dump(self, data: Union[List, Dict], many: bool):
        if many:
            return [dict(element) for element in data]

        return data


class RequestQueryPaginationSchema(Schema):
    offset = fields.Integer(missing=0, default=0, validate=validate.Range(min=0))


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


class HistorySchema(BaseSchema):
    id = fields.Integer(required=True)
    created_at = fields.DateTime(required=True)
    song_id = fields.Integer(required=True)
    song_title = fields.Str(required=True)
    channel_id = fields.Integer(required=True)
    bookmark_id = fields.Integer(default=0)


class HistoryInputSchema(HistorySchema):
    class Meta:
        dump_only = ("id", "created_at", "song_title", "bookmark_id")


class HistoryRequestQuerySchema(RequestQueryPaginationSchema):
    channel_id = fields.Integer(missing=0, default=0, validate=validate.Range(min=1))


class UserSchema(BaseSchema):
    id = fields.Integer(required=True, dump_only=True)
    sub = fields.String(required=True)
    picture = fields.Url(required=True)
    given_name = fields.Str(required=True)
    family_name = fields.Str(required=True)


class BookmarkSchema(BaseSchema):
    id = fields.Integer(required=True, dump_only=True)
    created_at = fields.DateTime(required=True, dump_only=True)
    song_id = fields.Integer(required=True)
    song_title = fields.Str(required=True, dump_only=True)
    user_id = fields.Integer(required=True)


class BookmarkRequestPathSchema(Schema):
    bookmark_id = fields.Integer(required=True, validate=validate.Range(min=1))


class BookmarksRequestQuerySchema(RequestQueryPaginationSchema):
    pass


class BookmarksRequestBodySchema(BookmarkSchema):
    class Meta:
        fields = ("song_id",)


class HTTPClientErrorSchema(Schema):
    detail = fields.Str(required=True)


class HTTPValidationErrorSchema(Schema):
    detail = fields.Dict(keys=fields.Str(), values=fields.List(fields.Dict(keys=fields.Str(),
                                                                           values=fields.List(fields.Str()))))


def request_validation(query_schema: Schema = None, body_schema: Schema = None, path_schema: Schema = None) -> Callable:
    def handler_wrapper(handler: Callable) -> Callable:
        @wraps(handler)
        async def request_wrapper(request: web.Request, **kwargs) -> Union[Callable, web.Response]:
            errors = {}

            if path_schema:
                try:
                    path = path_schema.load(dict(request.match_info))
                    request["path"] = path
                except ValidationError as e:
                    errors["path"] = e.messages

            if query_schema:
                try:
                    query = query_schema.load(dict(request.query))
                    request["query"] = query
                except ValidationError as e:
                    errors["query"] = e.messages

            if body_schema:
                try:
                    body = body_schema.load(await request.json())
                    request["body"] = body
                except JSONDecodeError as e:
                    raise web.HTTPUnsupportedMediaType()
                except ValidationError as e:
                    errors["body"] = e.messages

            if errors:
                validation_error_schema = HTTPValidationErrorSchema()
                data = validation_error_schema.dump({"detail": errors})
                raise web.HTTPUnprocessableEntity(text=json.dumps(data), content_type="application/json")

            return await handler(request, **kwargs)
        return request_wrapper
    return handler_wrapper
