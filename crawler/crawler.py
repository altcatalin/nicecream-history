import asyncio
import html
import logging
import re
from http import HTTPStatus
from typing import Dict, List

from aiohttp import ClientSession
from aioredis import create_redis
from databases import Database

from api.database import fetch_channels_extra, fetch_song_by_title, insert_song, insert_history_item, fetch_history_item
from api.settings import settings
from api.log import configure_logging


def extract(content: str):
    match = re.findall(r'\({\"songtitle\":\"(.+)\"}\)', content)
    song_title = re.sub('<.*?>', '', match[0])
    song_title = html.unescape(song_title)
    song_title = song_title.encode("ascii", "strict").decode("unicode-escape")
    return song_title


async def fetch_channel_content(channel: Dict, channel_url: str, session: ClientSession):
    async with session.get(channel_url) as response:
        return channel, response.status, await response.read()


async def fetch_channels_content(channels: List[Dict]):
    async with ClientSession(headers=settings["crawler"]["headers"]) as session:
        tasks = []

        for channel in channels:
            tasks.append(asyncio.ensure_future(fetch_channel_content(channel, channel["url"], session)))

        return await asyncio.gather(*tasks)


async def worker(forever: bool = True):
    await configure_logging()
    log = logging.getLogger(__name__)

    redis = await create_redis(settings["redis"]["url"])
    database = Database(settings["postgres"]["url"])
    await database.connect()

    while True:
        sleep_interval = settings["crawler"]["interval"]

        channels = await fetch_channels_extra(database)
        responses = await fetch_channels_content(channels)

        for channel, response_status_code, response_body in responses:
            if not response_status_code == HTTPStatus.OK:
                sleep_interval = settings["crawler"]["backoff_interval"]
                log.warning(f"channel_id={channel['id']}, status_code={response_status_code}")
                continue

            curr_song_title = extract(response_body.decode("utf8"))
            history_item_id = 0

            if not curr_song_title == channel["song_title"]:
                song = await fetch_song_by_title(database, curr_song_title)

                if not song:
                    song_id = await insert_song(database, curr_song_title)
                else:
                    song_id = song["id"]

                history_item_id = await insert_history_item(database, channel["id"], song_id)
                history_item = await fetch_history_item(database, history_item_id)
                redis.publish_json(settings["redis"]["channel"], history_item)

            log.info(f"channel_id={channel['id']}, status_code={response_status_code}, history_item_id={history_item_id}")

        if not forever:
            break

        await asyncio.sleep(sleep_interval)

    await database.disconnect()
    redis.close()


def main():
    try:
        asyncio.run(worker())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
