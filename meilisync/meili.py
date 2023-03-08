from typing import List, Optional, Type, Union

from meilisearch_python_async import Client

from meilisync.enums import EventType
from meilisync.event import EventCollection
from meilisync.plugin import Plugin
from meilisync.schemas import Event
from meilisync.settings import Sync


class Meili:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        plugins: Optional[List[Union[Type[Plugin], Plugin]]] = None,
    ):
        self.client = Client(
            api_url,
            api_key,
        )
        self.plugins = plugins or []

    async def add_full_data(self, index: str, pk: str, data: list):
        batch_size = 1000
        await self.client.index(index).add_documents_in_batches(
            data, batch_size=batch_size, primary_key=pk
        )

    async def delete_all_data(self, index: str):
        await self.client.index(index).delete_all_documents()

    async def get_count(self, index: str):
        stats = await self.client.index(index).get_stats()
        return stats.number_of_documents

    async def handle_events(self, collection: EventCollection):
        created_events, updated_events, deleted_events = collection.pop_events
        for sync, events in created_events.items():
            await self.handle_events_by_type(sync, events, EventType.create)
        for sync, events in updated_events.items():
            await self.handle_events_by_type(sync, events, EventType.update)
        for sync, events in deleted_events.items():
            await self.handle_events_by_type(sync, events, EventType.delete)

    async def handle_plugins_pre(self, sync: Sync, event: Event):
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
        return event

    async def handle_plugins_post(self, sync: Sync, event: Event):
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
        return event

    async def handle_events_by_type(self, sync: Sync, events: List[Event], event_type: EventType):
        if not events:
            return
        index = self.client.index(sync.index_name)
        for event in events:
            await self.handle_plugins_pre(sync, event)
        if event_type == EventType.create:
            await index.add_documents(
                [event.mapping_data(sync.fields) for event in events], primary_key=sync.pk
            )
        elif event_type == EventType.update:
            await index.update_documents(
                [event.mapping_data(sync.fields) for event in events], primary_key=sync.pk
            )
        elif event_type == EventType.delete:
            await index.delete_documents([str(event.data[sync.pk]) for event in events])
        for event in events:
            await self.handle_plugins_post(sync, event)

    async def handle_event(self, event: Event, sync: Sync):
        event = await self.handle_plugins_pre(sync, event)
        index = self.client.index(sync.index_name)
        if event.type == EventType.create:
            await index.add_documents([event.mapping_data(sync.fields)], primary_key=sync.pk)
        elif event.type == EventType.update:
            await index.update_documents([event.mapping_data(sync.fields)], primary_key=sync.pk)
        elif event.type == EventType.delete:
            await index.delete_documents([str(event.data[sync.pk])])
        await self.handle_plugins_post(sync, event)
