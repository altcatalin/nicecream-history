from aiohttp import web

from api.auth import *
from api.csrf import csrf_protection
from api.database import *
from api.logger import get_logger
from api.schemas import *
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
        description: Get all channels
        responses:
            200:
                description: Successful
                content:
                    application/json:
                        schema:
                            type: array
                            items: ChannelSchema
    """
    database = request.app["database"]
    data = await fetch_channels(database)
    return web.json_response(data)


@request_validation(query_schema=HistoryRequestQuerySchema())
async def get_history_handler(request: web.Request) -> web.Response:
    """Get history
    ---
    get:
        tags:
            - history
        summary: Get history
        description: Get up to 100 records per request.
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
                description: Successful
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
    session = await get_session(request)
    user_id = session["user_id"] if "user_id" in session else 0
    data = await fetch_history(database, request["query"], user_id)
    return web.json_response(data)


async def get_history_events_handler(request: web.Request) -> web.StreamResponse:
    """Get history
    ---
    get:
        tags:
            - history
        summary: Get history events
        description: |
            Get real-time notifications over a [SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) connection.
        security:
            - cookieAuth: []
        responses:
            200:
                description: Successful
                content:
                    text/event-stream:
                        schema:
                            type: string
                            example: 'id: 0\n\nevent: history\n\ndata: {\"song_id\": 0, \"id\": 0, \"bookmark_id\": 0, \"channel_id\": 0, \"song_title\": \"string\", \"created_at\": \"2019-07-03T15:32:02.632513+00:00\"}\n\nretry: 0\n\n'
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
    """Get user info
    ---
    get:
        tags:
            - user
        summary: Get user info
        security:
            - cookieAuth: []
        responses:
            200:
                description: Successful
                content:
                    application/json:
                        schema: UserSchema
            401:
                description: Unauthorized
                content:
                    application/json:
                        schema: HTTPClientErrorSchema
    """
    session = await get_session(request)
    database = request.app["database"]
    data = await fetch_user(database, session["user_id"])
    return web.json_response(data)


async def get_user_google_handler(request: web.Request) -> web.Response:
    """Sign in with Google OAuth 2.0
    ---
    get:
        tags:
            - user
        summary: Sign in with Google OAuth 2.0
        description: |
            Redirect to this path to initiate authentication and authorization process.

            [Using OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/OAuth2WebServer)
        responses:
            302:
                description: Successful
                headers:
                    Location:
                        type: "string"
    """
    authorization_url = await generate_google_authorization_url(request)
    return web.HTTPFound(authorization_url)


async def get_user_google_callback_handler(request: web.Request) -> web.Response:
    """Google OAuth 2.0 callback path
    ---
    get:
        tags:
            - user
        summary: Google OAuth 2.0 callback path
        description: |
            Google OAuth 2.0 will redirect the users to this path after after they have authenticated with Google.

            The server will set a session cookie if the authorization code is exchanged successfully for access & id tokens

            [Using OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/OAuth2WebServer)
        responses:
            302:
                description: Successful
                headers:
                    Location:
                        type: "string"
                    Set-Cookie:
                        schema:
                            type: string
                            example: JSESSIONID=abcde12345; Path=/; HttpOnly
    """
    await exchange_google_code_for_tokens(request)
    return web.HTTPFound(settings["spa"]["url"])


@private_path
async def get_user_sign_out_handler(request: web.Request) -> web.Response:
    """Sign out
    ---
    get:
        tags:
            - user
        summary: Sign out
        security:
            - cookieAuth: []
        responses:
            200:
                description: Successful
                headers:
                    Location:
                        type: "string"
    """
    session = await get_session(request)
    session.invalidate()
    return web.HTTPFound(settings["spa"]["url"])


@private_path
@request_validation(query_schema=BookmarksRequestQuerySchema())
async def get_user_bookmarks_handler(request: web.Request) -> web.Response:
    """Get user bookmarks
    ---
    get:
        tags:
            - user
        summary: Get user bookmarks
        description: Get up to 100 records per request.
        parameters:
            -
                name: offset
                in: query
                required: false
                description: Get records starting with the offset value, default = 0
                schema:
                    type: integer
        security:
            - cookieAuth: []
        responses:
            200:
                description: Successful
                content:
                    application/json:
                        schema:
                            type: array
                            items: BookmarkSchema
            401:
                description: Unauthorized
                content:
                    application/json:
                        schema: HTTPClientErrorSchema
            422:
                description: Validation Error
                content:
                    application/json:
                        schema: HTTPValidationErrorSchema
    """
    database = request.app["database"]
    session = await get_session(request)
    data = await fetch_bookmarks(database, request["query"], session["user_id"])
    return web.json_response(data)


@private_path
@csrf_protection
@request_validation(body_schema=BookmarksRequestBodySchema())
async def post_user_bookmarks_handler(request: web.Request) -> web.Response:
    """Add user bookmark
    ---
    post:
        tags:
            - user
        summary: Add user bookmark
        requestBody:
            required: true
            content:
                application/json:
                    schema: BookmarksRequestBodySchema
        security:
            - cookieAuth: []
        responses:
            200:
                description: Successful
                content:
                    application/json:
                        schema: BookmarkSchema
            401:
                description: Unauthorized
                content:
                    application/json:
                        schema: HTTPClientErrorSchema
            415:
                description: Unsupported Media Type
                content:
                    application/json:
                        schema: HTTPClientErrorSchema
            422:
                description: Validation Error
                content:
                    application/json:
                        schema: HTTPValidationErrorSchema
    """
    database = request.app["database"]
    session = await get_session(request)
    song = await fetch_song(database, request["body"]["song_id"])

    if not song:
        validation_error_schema = HTTPValidationErrorSchema()
        data = validation_error_schema.dump({"detail": {"body": {"song_id": ["Not found."]}}})
        raise web.HTTPUnprocessableEntity(text=json.dumps(data), content_type="application/json")

    bookmark = await fetch_bookmark_by_user_and_song(database, session["user_id"], request["body"]["song_id"])

    if bookmark:
        bookmark_id = bookmark["id"]
    else:
        bookmark_id = await insert_bookmark(database, session["user_id"], request["body"]["song_id"])

    data = await fetch_bookmark(database, bookmark_id)
    return web.json_response(data)


@private_path
@csrf_protection
@request_validation(path_schema=BookmarkRequestPathSchema())
async def delete_user_bookmarks_handler(request: web.Request) -> web.Response:
    """Delete user bookmark
    ---
    delete:
        tags:
            - user
        summary: Delete user bookmark
        parameters:
            -
                name: bookmark_id
                in: path
                required: true
                description: Bookmark ID
                schema:
                    type: integer
        security:
            - cookieAuth: []
        responses:
            200:
                description: Successful
                content:
                    application/json:
                        schema:
                            type: object
            401:
                description: Unauthorized
                content:
                    application/json:
                        schema: HTTPClientErrorSchema
            404:
                description: Not Found
                content:
                    application/json:
                        schema: HTTPClientErrorSchema
            422:
                description: Validation Error
                content:
                    application/json:
                        schema: HTTPValidationErrorSchema
    """
    database = request.app["database"]
    session = await get_session(request)
    data = await fetch_bookmark(database, request["path"]["bookmark_id"])

    if data["user_id"] != session["user_id"]:
        raise web.HTTPNotFound()

    await delete_bookmark(database, request["path"]["bookmark_id"])
    return web.json_response({})
