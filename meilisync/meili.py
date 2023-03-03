import functools
from typing import List, Optional, Type, Union

from loguru import logger
from meilisearch_python_async import Client

from meilisync.enums import EventType
from meilisync.plugin import Plugin
from meilisync.schemas import Event
from meilisync.settings import MeiliSearch, Sync


class Meili:
    def __init__(
        self,
        debug: bool,
        meilisearch: MeiliSearch,
        sync: List[Sync],
        plugins: Optional[List[Union[Type[Plugin], Plugin]]] = None,
    ):
        self.client = Client(
            meilisearch.api_url,
            meilisearch.api_key,
        )
        self.sync = sync
        self.debug = debug
        self.plugins = plugins or []

    @functools.lru_cache()
    def _get_sync(self, table: str):
        for sync in self.sync:
            if sync.table == table:
                return sync

    async def add_full_data(self, index: str, pk: str, data: list):
        batch_size = 1000
        await self.client.index(index).add_documents_in_batches(
            data, batch_size=batch_size, primary_key=pk
        )

    async def handle_event(self, event: Event):
        if self.debug:
            logger.debug(event)
        table = event.table
        sync = self._get_sync(table)
        if not sync:
            return
        for plugin in self.plugins:
            if isinstance(plugin, Plugin):
                event = await plugin.pre_event(event)
            else:
                event = await plugin().pre_event(event)
        for plugin in sync.plugins_cls():
            if isinstance(plugin, Plugin):
                event = await plugin.pre_event(event)
            else:
                event = await plugin().pre_event(event)
        index = self.client.index(sync.index_name)
        if event.type == EventType.create:
            await index.add_documents([event.mapping_data(sync.fields)], primary_key=sync.pk)
        elif event.type == EventType.update:
            await index.update_documents([event.mapping_data(sync.fields)], primary_key=sync.pk)
        elif event.type == EventType.delete:
            await index.delete_documents([str(event.data[sync.pk])])
        for plugin in self.plugins:
            if isinstance(plugin, Plugin):
                event = await plugin.post_event(event)
            else:
                event = await plugin().post_event(event)
        for plugin in sync.plugins_cls():
            if isinstance(plugin, Plugin):
                event = await plugin.post_event(event)
            else:
                event = await plugin().post_event(event)
