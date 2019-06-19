import asyncio
import logging
from _weakrefset import WeakSet
from typing import Optional, Dict

from aiohttp import web
from aiohttp.typedefs import LooseHeaders
from aiohttp_sse import EventSourceResponse, _ContextManager

from api.cors import generate_cors_headers
from api.schemas import HistorySchema
from api.settings import settings


log = logging.getLogger(__name__)


class SSEResponse(EventSourceResponse):
    def __init__(self, *,
                 status: int = 200,
                 reason: Optional[str] = None,
                 headers: Optional[LooseHeaders] = None) -> None:
        super().__init__(status=status, reason=reason)

        if headers is not None:
            self.headers.extend(headers)

        self.headers.extend(generate_cors_headers())
        self.headers['X-Accel-Buffering'] = 'no'  # Nginx unbuffered responses for HTTP streaming application

    async def prepare(self, request: web.Request) -> None:
        if not self.prepared:
            await super().prepare(request)
        else:
            # hackish way to check if connection alive
            # should be updated once we have proper API in aiohttp
            # https://github.com/aio-libs/aiohttp/issues/3105
            if request.protocol.transport is None:
                # request disconnected
                raise asyncio.CancelledError()

    def enable_compression(self, force: bool = False) -> None:
        raise NotImplementedError


def sse_response(request: web.Request, *, status: int = 200, reason: str = None, headers: Dict = None) -> _ContextManager:
    sse = SSEResponse(status=status, reason=reason, headers=headers)
    return _ContextManager(sse._prepare(request))


async def create_sse_redis_subscriber(app: web.Application) -> None:
    app["sse_streams"] = WeakSet()
    app["sse_subscriber"] = asyncio.create_task(sse_redis_subscriber(app))


async def cancel_sse_redis_subscriber(app: web.Application) -> None:
    try:
        if not app["sse_subscriber"].cancelled():
            app["sse_subscriber"].cancel()
            await app["sse_subscriber"]
    except asyncio.CancelledError:
        pass


async def close_sse_streams(app: web.Application) -> None:
    waiters = []

    for stream in app["sse_streams"]:
        stream.stop_streaming()
        waiters.append(stream.wait())

    await asyncio.gather(*waiters)
    app["sse_streams"].clear()


async def sse_redis_subscriber(app: web.Application) -> None:
    channel, *_ = await app["redis"].subscribe(settings["redis"]["channel"])
    history_schema = HistorySchema()

    try:
        async for message in channel.iter(encoding="utf-8"):
            history = history_schema.loads(message)
            fs = []

            for stream in app['sse_streams']:
                fs.append(stream.send(message,
                                      id=history["id"],
                                      event=settings["redis"]["channel"],
                                      retry=settings["sse"]["retry"]))

            await asyncio.gather(*fs)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.exception(f"Fatal error in Redis subscriber", exc_info=True)
    finally:
        await app["redis"].unsubscribe(channel.name)
        await close_sse_streams(app)
        await cancel_sse_redis_subscriber(app)
