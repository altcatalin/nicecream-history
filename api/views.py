import base64
import json
from http import HTTPStatus

import aiohttp
from typing import Union

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp_session import get_session

from api.auth import private_path, generate_google_authorization_url, exchange_google_code_for_tokens, get_user_info
from api.database import fetch_channels, fetch_history
from api.logger import get_logger
from api.schemas import HistoryRequestFiltersSchema, request_path_schema, UserSchema
from api.settings import settings
from api.sse import sse_response


log = get_logger(__name__)


async def get_channels_handler(request: web.Request) -> web.Response:
    """Get channels
    ---
    get:
        tags:
            - channels
        summary: Get channels
        description: Retrieve all channels
        responses:
            200:
                description: Successful Response
                content:
                    application/json:
                        schema:
                            type: array
                            items: ChannelSchema
    """
    database = request.app["database"]
    data = await fetch_channels(database)

    return web.json_response(data)


@request_path_schema(HistoryRequestFiltersSchema())
async def get_history_handler(request: web.Request) -> Union[web.Response, web.StreamResponse]:
    """Get history
    ---
    get:
        tags:
            - history
        summary: Get history
        description: |
            Retrieve max 100 records from history.
        parameters:
            -
                name: channel_id
                in: query
                required: false
                description: Retrieve records filtered by channel ID, default = 0
                schema:
                    type: integer
            -
                name: offset
                in: query
                required: false
                description: Retrieve records starting with the offset value, default = 0
                schema:
                    type: integer
        responses:
            200:
                description: Successful Response
                content:
                    application/json:
                        schema:
                            type: array
                            items: HistorySchema
            422:
                description: Validation Error
                content:
                    application/json:
                        schema: HTTPValidationErrorSchema
    """
    database = request.app["database"]
    data = await fetch_history(database, request["parameters"])

    return web.json_response(data)


@request_path_schema(HistoryRequestFiltersSchema())
async def get_history_events_handler(request: web.Request) -> Union[web.Response, web.StreamResponse]:
    """Get history
    ---
    get:
        tags:
            - history
        summary: Get history events
        description: |
            Receive real-time notifications over a [SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) connection.
        parameters:
            -
                name: channel_id
                in: query
                required: false
                description: Retrieve records filtered by channel ID, default = 0
                schema:
                    type: integer
            -
                name: offset
                in: query
                required: false
                description: Retrieve records starting with the offset value, default = 0
                schema:
                    type: integer
        responses:
            200:
                description: Successful Response
                content:
                    text/event-stream:
                        schema:
                            type: string
                            example: 'id: 0\n\nevent: history\n\ndata: {\"song_id\": 0, \"id\": 0, \"channel_id\": 0, \"song_title\": \"string\", \"created_at\": \"2019-07-03T15:32:02.632513+00:00\"}\n\nretry: 0\n\n'
            422:
                description: Validation Error
                content:
                    application/json:
                        schema: HTTPValidationErrorSchema
    """

    # reject SSE connection if sse_subscriber background task is cancelled
    if request.app["sse_subscriber"].cancelled():
        raise web.HTTPInternalServerError()

    log.info("Opening a SSE connection")

    sse_stream = await sse_response(request)
    request.app["sse_streams"].add(sse_stream)

    try:
        await sse_stream.wait()
    finally:
        log.info("Closing a SSE connection")
        request.app["sse_streams"].discard(sse_stream)

    return sse_stream


@private_path
async def get_user_handler(request: web.Request) -> web.Response:
    """Get signed in user info
    ---
    get:
        tags:
            - user
        summary: Get signed in user info
        responses:
            200:
                description: Successful Response
                content:
                    application/json:
                        schema:
                            type: array
                            items: ChannelSchema
    """
    data = await get_user_info(request)
    return web.json_response(data)


async def get_user_google_handler(request: web.Request) -> web.Response:
    """Sign in with Google
    ---
    get:
        tags:
            - user
        summary: Sign in with Google
        description: |
            Redirect to this endpoint to initiate [OAuth 2.0 Authorization Code Grant](https://developers.google.com/identity/protocols/OAuth2WebServer)
        responses:
            302:
                description: Successful Response
                headers:
                    Location:
                        type: "string"
    """
    authorization_url = await generate_google_authorization_url(request)
    return web.HTTPFound(authorization_url)


async def get_user_google_callback_handler(request: web.Request) -> web.Response:
    """Google OAuth 2.0 Authorization Code Grant callback endpoint
    ---
    get:
        tags:
            - user
        summary: Google OAuth 2.0 Authorization Code Grant callback endpoint
        description: |
            This endpoint must be present in the Google client's authorized redirect URIs list
        responses:
            302:
                description: Successful Response
                headers:
                    Location:
                        type: "string"
    """
    await exchange_google_code_for_tokens(request)
    return web.HTTPFound(settings["spa"]["url"])
