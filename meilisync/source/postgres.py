import json
import threading
from queue import Queue
from typing import List

import psycopg2
import psycopg2.errors
from psycopg2._psycopg import ReplicationMessage
from psycopg2.extras import LogicalReplicationConnection

from meilisync.enums import EventType, SourceType
from meilisync.schemas import Event, ProgressEvent
from meilisync.settings import Sync
from meilisync.source import Source


class Postgres(Source):
    type = SourceType.postgres
    slot = "meilisync"

    def __init__(
        self,
        progress: dict,
        tables: List[str],
        **kwargs,
    ):
        super().__init__(progress, tables, **kwargs)
        self.conn = psycopg2.connect(**self.kwargs, connection_factory=LogicalReplicationConnection)
        self.cursor = self.conn.cursor()
        self.queue: Queue[Event] = Queue()
        if self.progress:
            self.start_lsn = self.progress["start_lsn"]
        else:
            self.cursor.execute("SELECT pg_current_wal_lsn()")
            self.start_lsn = self.cursor.fetchone()[0]

    async def get_full_data(self, sync: Sync):
        conn = psycopg2.connect(**self.kwargs, cursor_factory=psycopg2.extras.RealDictCursor)
        with conn.cursor() as cur:
            if sync.fields_mapping:
                fields = ", ".join(
                    f"{field} as {sync.fields_mapping[field]}" for field in sync.fields_mapping
                )
            else:
                fields = "*"
            cur.execute(f"SELECT {fields} FROM {sync.table}")
            ret = cur.fetchall()
            return ret

    def _consumer(self, msg: ReplicationMessage):
        payload = json.loads(msg.payload)
        changes = payload.get("change")
        if not changes:
            return
        for change in changes:
            kind = change.get("kind")
            table = change.get("table")
            if table not in self.tables:
                return
            columnnames = change.get("columnnames")
            columnvalues = change.get("columnvalues")
            values = dict(zip(columnnames, columnvalues))
            if kind == "update":
                event_type = EventType.update
            elif kind == "delete":
                event_type = EventType.delete
            elif kind == "insert":
                event_type = EventType.create
            else:
                return
            self.queue.put(
                Event(
                    type=event_type,
                    table=table,
                    data=values,
                    progress={"start_lsn": payload.get("nextlsn")},
                )
            )

    async def __aiter__(self):
        try:
            self.cursor.create_replication_slot(self.slot, output_plugin="wal2json")
        except psycopg2.errors.DuplicateObject:  # type: ignore
            pass
        self.cursor.start_replication(
            slot_name=self.slot,
            decode=True,
            status_interval=1,
            start_lsn=self.start_lsn,
            options={
                "include-lsn": "true",
            },
        )
        t = threading.Thread(target=self.cursor.consume_stream, args=(self._consumer,))
        t.setDaemon(True)
        t.start()
        yield ProgressEvent(
            progress={"start_lsn": self.start_lsn},
        )
        while True:
            yield self.queue.get()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.conn.close()
