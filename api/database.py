from typing import List, Dict, Mapping

from aiohttp import web
from databases import Database
from sqlalchemy import desc, select

from api.schemas import ChannelSchema, HistorySchema, ChannelExtraSchema, SongSchema, HistoryInSchema, \
    HistoryRequestFiltersSchema
from api.settings import settings


from sqlalchemy import MetaData, Table, Column, Integer, String, Index, DateTime, func, ForeignKey

meta = MetaData()

channels_table = Table("channels", meta,
                       Column("id",  Integer, primary_key=True, nullable=False),
                       Column("name", String(10), nullable=False),
                       Column("url", String(200), nullable=False))

songs_table = Table("songs", meta,
                    Column("id",  Integer, primary_key=True, nullable=False),
                    Column("title", String(200), index=Index(name="ix_songs_title", postgresql_using="hash"), nullable=False))

history_table = Table("history", meta,
                      Column("id",  Integer, primary_key=True, nullable=False),
                      Column("created_at", DateTime, server_default=func.now(), nullable=False),
                      Column("song_id", Integer, ForeignKey("songs.id", ondelete='RESTRICT'), nullable=False),
                      Column("channel_id", Integer, ForeignKey("channels.id", ondelete='RESTRICT'), nullable=False))


async def create_postgres_connection_pool(app: web.Application) -> None:
    database = Database(app["settings"]["postgres"]["url"])
    await database.connect()
    app["database"] = database


async def close_postgres_connection_pool(app: web.Application) -> None:
    await app["database"].disconnect()


async def fetch_channels(database: Database) -> List[Dict]:
    channel_schema = ChannelSchema(many=True)
    query = channels_table.select()
    rows = await database.fetch_all(query)
    data = channel_schema.dump(rows)
    return data


async def fetch_channels_extra(database: Database) -> List[Dict]:
    channel_extra_schema = ChannelExtraSchema(many=True)
    subquery = select([history_table.c.channel_id, songs_table]) \
        .distinct(history_table.c.channel_id) \
        .select_from(history_table.outerjoin(songs_table)) \
        .order_by(history_table.c.channel_id, desc(history_table.c.id)) \
        .lateral("channels_last_songs")
    query = select([channels_table,
                    subquery.c.id.label("song_id"),
                    subquery.c.title.label("song_title")]) \
        .select_from(channels_table.outerjoin(subquery, channels_table.c.id == subquery.c.channel_id))

    rows = await database.fetch_all(query)
    data = channel_extra_schema.dump(rows)
    return data


async def fetch_song_by_title(database: Database, title: str) -> Dict:
    song_schema = SongSchema()
    query = songs_table.select().where(songs_table.c.title == title)
    row = await database.fetch_one(query)
    return song_schema.dump(row)


async def insert_song(database: Database, title: str) -> int:
    song_schema = SongSchema()
    query = songs_table.insert()
    values = song_schema.load({"title": title})
    song_id = await database.execute(query=query, values=values)
    return song_id


async def fetch_history(database: Database, parameters: HistoryRequestFiltersSchema.dump) -> List[Dict]:
    history_schema = HistorySchema(many=True)
    query = select([history_table, songs_table.c.title.label('song_title')]) \
        .select_from(history_table.outerjoin(songs_table)) \
        .order_by(desc(history_table.c.id))\
        .limit(settings["pagination"]["limit"])\
        .offset(parameters["offset"])

    if parameters["channel_id"]:
        query = query.where(history_table.c.channel_id == parameters["channel_id"])

    rows = await database.fetch_all(query)
    data = history_schema.dump(rows)
    return data


async def fetch_history_item(database: Database, history_id: int) -> Dict:
    history_schema = HistorySchema()
    query = select([history_table, songs_table.c.title.label('song_title')]) \
        .select_from(history_table.outerjoin(songs_table)) \
        .where(history_table.c.id == history_id)
    row = await database.fetch_one(query)
    data = history_schema.dump(row)
    return data


async def insert_history_item(database: Database, channel_id: int, song_id: int) -> int:
    history_schema = HistoryInSchema()
    query = history_table.insert()
    values = history_schema.load({"channel_id": channel_id, "song_id": song_id})
    history_id = await database.execute(query=query, values=values)
    return history_id
