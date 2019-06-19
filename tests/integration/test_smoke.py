import asyncio

import pytest

from api.api import build
from crawler.crawler import worker


def test_worker():
    asyncio.run(worker(False))


async def test_history(aiohttp_client):
    app = await build()

    client = await aiohttp_client(app)

    response = await client.get('/history')
    body = await response.json()

    try:
        await client.close()
    except asyncio.CancelledError:
        pass

    assert response.status == 200
    assert len(body) > 0
