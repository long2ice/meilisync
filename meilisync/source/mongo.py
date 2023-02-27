from asyncio import sleep
from typing import List

import motor.motor_asyncio
import pymongo
from pymongo import CursorType

from meilisync.enums import SourceType
from meilisync.schemas import Event, ProgressEvent
from meilisync.settings import Sync
from meilisync.source import Source


class Mongo(Source):
    type = SourceType.mongo

    def __init__(self, progress: dict, tables: List[str], **kwargs):
        super().__init__(progress, tables, **kwargs)
        database = self.kwargs.pop("database")
        self.client = motor.motor_asyncio.AsyncIOMotorClient(**self.kwargs)
        self.db = self.client[database]

    async def get_full_data(self, sync: Sync):
        collection = self.db[sync.table]
        if sync.fields:
            fields = {field: sync.fields[field] for field in sync.fields}
        else:
            fields = {}
        cursor = collection.find({}, fields)
        ret = []
        async for doc in cursor:
            ret.append(doc)
        return ret

    async def __aiter__(self):
        oplog = self.client.local.oplog.rs
        if self.progress:
            ts = self.progress["ts"]
        else:
            try:
                first = await oplog.find().sort("$natural", pymongo.ASCENDING).limit(-1).next()
                ts = first["ts"]
            except StopAsyncIteration:
                ts = 0

        yield ProgressEvent(
            progress={
                "ts": ts,
            }
        )
        while True:
            cursor = oplog.find(
                {"ts": {"$gt": ts}}, cursor_type=CursorType.TAILABLE_AWAIT, oplog_replay=True
            )
            while cursor.alive:
                async for doc in cursor:
                    ts = doc["ts"]
                    yield Event(
                        type=doc["op"],
                        table=doc["ns"].split(".")[1],
                        data=doc["o"],
                        progress={"ts": ts},
                    )
                await sleep(1)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
