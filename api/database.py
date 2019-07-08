from typing import List, Dict, Mapping

from aiohttp import web
from databases import Database
from sqlalchemy import desc, select, CHAR

from api.schemas import *
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


users_table = Table("users", meta,
                    Column("id",  Integer, primary_key=True, nullable=False),
                    Column("sub", CHAR(21), index=True, nullable=False),
                    Column("picture", String(200), nullable=True),
                    Column("given_name", String(50), nullable=False),
                    Column("family_name", String(50), nullable=False))

bookmarks_table = Table("bookmarks", meta,
                        Column("id",  Integer, primary_key=True, nullable=False),
                        Column("created_at", DateTime, server_default=func.now(), nullable=False),
                        Column("user_id", Integer, ForeignKey("users.id", ondelete='RESTRICT'), nullable=False),
                        Column("song_id", Integer, ForeignKey("songs.id", ondelete='RESTRICT'), nullable=False))


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


async def fetch_song(database: Database, song_id: int) -> Dict:
    song_schema = SongSchema()
    query = songs_table.select().where(songs_table.c.id == song_id)
    row = await database.fetch_one(query)
    return song_schema.dump(row)


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


async def fetch_history(database: Database, parameters: HistoryRequestQuerySchema.dump, user_id: int = 0) -> List[Dict]:
    history_schema = HistorySchema(many=True)
    query = select([history_table, songs_table.c.title.label('song_title')]) \
        .select_from(history_table.outerjoin(songs_table)) \
        .order_by(desc(history_table.c.id))\
        .limit(settings["pagination"]["limit"])\
        .offset(parameters["offset"])

    if parameters["channel_id"]:
        query = query.where(history_table.c.channel_id == parameters["channel_id"])

    history_rows = await database.fetch_all(query)
    song_ids = []

    if history_rows and user_id:
        bookmark_schema = BookmarkSchema(many=True)
        song_ids = [item["song_id"] for item in history_rows]

        bookmarks_query = select([bookmarks_table],
                                 bookmarks_table.c.song_id.in_(song_ids))\
            .where(bookmarks_table.c.user_id == user_id)
        bookmarks_rows = await database.fetch_all(bookmarks_query)
        bookmarks = bookmark_schema.dump(bookmarks_rows)
        song_bookmarks = {bookmark["song_id"] : bookmark["id"] for bookmark in bookmarks}

        def mapper(item):
            item = dict(item)
            item["bookmark_id"] = song_bookmarks[item["song_id"]] if item["song_id"] in song_bookmarks else 0
            return item

        history_rows = list(map(mapper, history_rows))

    history = history_schema.dump(history_rows)
    return history


async def fetch_history_item(database: Database, history_id: int) -> Dict:
    history_schema = HistorySchema()
    query = select([history_table, songs_table.c.title.label('song_title')]) \
        .select_from(history_table.outerjoin(songs_table)) \
        .where(history_table.c.id == history_id)
    row = await database.fetch_one(query)
    data = history_schema.dump(row)
    return data


async def insert_history_item(database: Database, channel_id: int, song_id: int) -> int:
    history_schema = HistoryInputSchema()
    query = history_table.insert()
    values = history_schema.load({"channel_id": channel_id, "song_id": song_id})
    history_id = await database.execute(query=query, values=values)
    return history_id


async def fetch_user(database: Database, user_id: int) -> Dict:
    user_schema = UserSchema()
    query = users_table.select().where(users_table.c.id == user_id)
    row = await database.fetch_one(query)
    data = user_schema.dump(row)
    return data


async def fetch_user_by_sub(database: Database, sub: str) -> Dict:
    user_schema = UserSchema()
    query = users_table.select().where(users_table.c.sub == sub)
    row = await database.fetch_one(query)
    data = user_schema.dump(row)
    return data


async def insert_user(database: Database, sub: str, given_name: str, family_name: str, picture: str) -> int:
    user_schema = UserSchema()
    query = users_table.insert()
    values = user_schema.load({"sub": sub, "given_name": given_name, "family_name": family_name, "picture": picture})
    user_id = await database.execute(query=query, values=values)
    return user_id


async def update_user(database: Database, given_name: str, family_name: str, picture: str) -> None:
    user_schema = UserSchema(exclude=("sub",))
    query = users_table.update()
    values = user_schema.load({"given_name": given_name, "family_name": family_name, "picture": picture})
    await database.execute(query=query, values=values)


async def fetch_bookmarks(database: Database, parameters: BookmarksRequestQuerySchema.dump, user_id: int = 0) -> List[Dict]:
    bookmark_schema = BookmarkSchema(many=True)
    query = select([bookmarks_table, songs_table.c.title.label('song_title')]) \
        .select_from(bookmarks_table.outerjoin(songs_table)) \
        .order_by(desc(bookmarks_table.c.id))\
        .limit(settings["pagination"]["limit"])\
        .offset(parameters["offset"])

    if user_id:
        query = query.where(bookmarks_table.c.user_id == user_id)

    rows = await database.fetch_all(query)
    data = bookmark_schema.dump(rows)
    return data


async def fetch_bookmark(database: Database, bookmark_id: int) -> Dict:
    bookmark_schema = BookmarkSchema()
    query = select([bookmarks_table, songs_table.c.title.label('song_title')]) \
        .select_from(bookmarks_table.outerjoin(songs_table)) \
        .where(bookmarks_table.c.id == bookmark_id)
    row = await database.fetch_one(query)
    data = bookmark_schema.dump(row)
    return data


async def fetch_bookmark_by_user_and_song(database: Database, user_id: int, song_id: int) -> Dict:
    bookmark_schema = BookmarkSchema()
    query = select([bookmarks_table, songs_table.c.title.label('song_title')]) \
        .select_from(bookmarks_table.outerjoin(songs_table)) \
        .where(bookmarks_table.c.user_id == user_id)\
        .where(bookmarks_table.c.song_id == song_id)
    row = await database.fetch_one(query)
    data = bookmark_schema.dump(row)
    return data


async def insert_bookmark(database: Database, user_id: int, song_id: int) -> int:
    bookmark_schema = BookmarkSchema()
    query = bookmarks_table.insert()
    values = bookmark_schema.load({"user_id": user_id, "song_id": song_id})
    bookmark_id = await database.execute(query=query, values=values)
    return bookmark_id


async def delete_bookmark(database: Database, bookmark_id: int) -> None:
    query = bookmarks_table.delete().where(bookmarks_table.c.id == bookmark_id)
    await database.execute(query=query)
