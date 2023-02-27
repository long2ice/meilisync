from typing import List

import asyncmy
from asyncmy.cursors import DictCursor
from asyncmy.replication import BinLogStream
from asyncmy.replication.row_events import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)

from meilisync.enums import EventType, SourceType
from meilisync.schemas import Event, ProgressEvent
from meilisync.settings import Sync
from meilisync.source import Source


class MySQL(Source):
    type = SourceType.mysql

    def __init__(
        self,
        progress: dict,
        tables: List[str],
        server_id: int = 1,
        **kwargs,
    ):
        super().__init__(progress, tables, **kwargs)
        self.server_id = server_id
        self.database = kwargs.get("database")

    async def get_full_data(self, sync: Sync):
        conn = await asyncmy.connect(**self.kwargs)
        if sync.fields:
            fields = ", ".join(f"{field} as {sync.fields[field] or field}" for field in sync.fields)
        else:
            fields = "*"
        async with conn.cursor(cursor=DictCursor) as cur:
            await cur.execute(f"SELECT {fields} FROM {sync.table}")
            ret = await cur.fetchall()
            return ret

    async def _get_binlog_position(self):
        async with self.conn.cursor(cursor=DictCursor) as cur:
            await cur.execute("SHOW MASTER STATUS")
            ret = await cur.fetchone()
            return ret["File"], ret["Position"]

    async def __aiter__(self):
        self.conn = await asyncmy.connect(**self.kwargs)
        self.ctl_conn = await asyncmy.connect(**self.kwargs)
        if self.progress:
            master_log_file = self.progress["master_log_file"]
            master_log_position = int(self.progress["master_log_position"])
        else:
            master_log_file, master_log_position = await self._get_binlog_position()
        yield ProgressEvent(
            progress={
                "master_log_file": master_log_file,
                "master_log_position": master_log_position,
            }
        )
        stream = BinLogStream(
            self.conn,
            self.ctl_conn,
            server_id=self.server_id,
            master_log_file=master_log_file,
            master_log_position=master_log_position,
            resume_stream=True,
            blocking=True,
            only_schemas=[self.database],
            only_tables=[f"{self.database}.{table}" for table in self.tables],
            only_events=[WriteRowsEvent, UpdateRowsEvent, DeleteRowsEvent],
        )
        async for event in stream:
            if isinstance(event, WriteRowsEvent):
                event_type = EventType.create
                data = event.rows[0]["values"]
            elif isinstance(event, UpdateRowsEvent):
                event_type = EventType.update
                data = event.rows[0]["after_values"]
            elif isinstance(event, DeleteRowsEvent):
                event_type = EventType.delete
                data = event.rows[0]["values"]
            else:
                continue
            yield Event(
                type=event_type,
                table=event.table,
                data=data,
                progress=dict(
                    master_log_file=stream._master_log_file,
                    master_log_position=stream._master_log_position,
                ),
            )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        self.ctl_conn.close()
