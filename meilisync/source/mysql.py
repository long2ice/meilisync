import asyncio
from typing import List

import asyncmy
from asyncmy.cursors import DictCursor
from asyncmy.replication import BinLogStream
from asyncmy.replication.row_events import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)
from loguru import logger

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
        self.server_id = int(server_id)
        self.database = kwargs.get("database")

    async def get_full_data(self, sync: Sync, size: int):
        conn = await asyncmy.connect(**self.kwargs)
        if sync.fields:
            fields = ", ".join(f"{field} as {sync.fields[field] or field}" for field in sync.fields)
        else:
            fields = "*"
        async with conn.cursor(cursor=DictCursor) as cur:
            offset = 0
            while True:
                await cur.execute(
                    f"SELECT {fields} FROM {sync.table} "
                    f"ORDER BY {sync.pk} LIMIT {size} OFFSET {offset}"
                )
                ret = await cur.fetchall()
                if not ret:
                    break
                offset += size
                yield ret

    async def get_count(self, sync: Sync):
        conn = await asyncmy.connect(**self.kwargs)
        async with conn.cursor(cursor=DictCursor) as cur:
            await cur.execute(f"SELECT COUNT(*) as count FROM {sync.table}")
            ret = await cur.fetchone()
            return ret["count"]

    async def ping(self):
        async with asyncmy.connect(**self.kwargs) as conn:
            return await conn.ping()

    async def get_current_progress(self):
        async with asyncmy.connect(**self.kwargs) as conn:
            async with conn.cursor(cursor=DictCursor) as cur:
                await cur.execute("SHOW MASTER STATUS")
                ret = await cur.fetchone()
                return {
                    "master_log_file": ret["File"],
                    "master_log_position": ret["Position"],
                }

    async def _check_process(self):
        sql = "SELECT * FROM information_schema.PROCESSLIST WHERE COMMAND=%s AND DB=%s"
        async with asyncmy.connect(**self.kwargs) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, ("Binlog Dump", self.database))
                ret = await cur.fetchone()
                if not ret:
                    logger.warning("Binlog Dump process not found, restart it...")
                    await self.stream.close()

    async def _start_check_process(self):
        while True:
            await asyncio.sleep(60)
            try:
                await self._check_process()
            except Exception as e:
                logger.exception(e)

    async def __aiter__(self):
        asyncio.ensure_future(self._start_check_process())
        self.conn = await asyncmy.connect(**self.kwargs)
        self.ctl_conn = await asyncmy.connect(**self.kwargs)
        if self.progress:
            master_log_file = self.progress["master_log_file"]
            master_log_position = int(self.progress["master_log_position"])
        else:
            progress = await self.get_current_progress()
            master_log_file = progress["master_log_file"]
            master_log_position = int(progress["master_log_position"])
        yield ProgressEvent(
            progress={
                "master_log_file": master_log_file,
                "master_log_position": master_log_position,
            }
        )
        self.stream = BinLogStream(
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
        async for event in self.stream:
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
                    master_log_file=self.stream._master_log_file,
                    master_log_position=self.stream._master_log_position,
                ),
            )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        self.ctl_conn.close()
