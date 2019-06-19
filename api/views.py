from typing import Union

from aiohttp import web, hdrs

from api.database import fetch_channels, fetch_history
from api.schemas import HistoryRequestFiltersSchema, request_path_schema
from api.sse import sse_response


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
                    application/json:
                        schema:
                            type: array
                            items: HistorySchema
                    text/event-stream:
                        schema: HistorySchema
            422:
                description: Validation Error
                content:
                    application/json:
                        schema: HTTPValidationErrorSchema
    """
    accept_header = request.headers.get(hdrs.ACCEPT)

    # return a SSE response
    if accept_header == "text/event-stream":

        # reject SSE connection if sse_subscriber background task is cancelled
        if request.app["sse_subscriber"].cancelled():
            raise web.HTTPInternalServerError()

        sse_stream = await sse_response(request)
        request.app["sse_streams"].add(sse_stream)

        try:
            await sse_stream.wait()
        finally:
            request.app["sse_streams"].discard(sse_stream)

        return sse_stream

    database = request.app["database"]
    data = await fetch_history(database, request["parameters"])

    return web.json_response(data)
