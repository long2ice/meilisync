from typing import List

import motor.motor_asyncio

from meilisync.enums import EventType, SourceType
from meilisync.schemas import Event
from meilisync.settings import Sync
from meilisync.source import Source


class Mongo(Source):
    type = SourceType.mongo

    def __init__(self, progress: dict, tables: List[str], **kwargs):
        super().__init__(progress, tables, **kwargs)
        database = self.kwargs.pop("database")
        self.client = motor.motor_asyncio.AsyncIOMotorClient(**self.kwargs)  # type: ignore
        self.db = self.client[database]

    async def get_full_data(self, sync: Sync, size: int):
        collection = self.db[sync.table]
        if sync.fields:
            fields = {field: sync.fields[field] for field in sync.fields}
        else:
            fields = {}
        cursor = collection.find({}, fields)
        ret = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            ret.append(doc)
            if len(ret) == size:
                yield ret
                ret = []
        if ret:
            yield ret

    async def get_count(self, sync: Sync):
        collection = self.db[sync.table]
        return await collection.count_documents({})

    async def ping(self):
        return await self.client.admin.command("ping")

    async def get_current_progress(self):
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "delete"]}}}]
        async with self.db.watch(pipeline) as stream:
            return {"resume_token": stream.resume_token}

    async def __aiter__(self):
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "delete"]}}}]
        if self.progress:
            resume_token = self.progress["resume_token"]
        else:
            resume_token = None
        async with self.db.watch(pipeline, resume_after=resume_token) as stream:
            async for change in stream:
                resume_token = stream.resume_token
                operation_type = change["operationType"]
                if operation_type == "insert":
                    event_type = EventType.create
                    data = change["fullDocument"]
                elif operation_type == "update":
                    event_type = EventType.update
                    data = change["updateDescription"]["updatedFields"]
                elif operation_type == "delete":
                    event_type = EventType.delete
                    data = change["documentKey"]
                data["_id"] = str(change["documentKey"]["_id"])
                yield Event(
                    type=event_type,
                    table=change["ns"]["coll"],
                    data=data,
                    progress=dict(resume_token=resume_token),
                )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
