import asyncio
from typing import AsyncGenerator, List, Optional, Type, Union

from loguru import logger
from meilisearch_python_sdk import AsyncClient
from meilisearch_python_sdk.errors import MeilisearchApiError

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
        wait_for_task_timeout: Optional[int] = None,
    ):
        self.client = AsyncClient(
            api_url,
            api_key,
        )
        self.plugins = plugins or []
        self.wait_for_task_timeout = wait_for_task_timeout

    async def add_data(self, sync: Sync, data: list):
        events = [Event(type=EventType.create, data=item, table=sync.table) for item in data]
        return await self.handle_events_by_type(sync, events, EventType.create)

    async def refresh_data(self, sync: Sync, data: AsyncGenerator, keep_index: bool = False):
        index = sync.index_name
        pk = sync.pk
        if not keep_index:
            sync.index = index_name_tmp = f"{index}_tmp"
            try:
                await self.client.index(index_name_tmp).delete()
            except MeilisearchApiError as e:
                if e.code != "MeilisearchApiError.index_not_found":
                    raise
            settings = await self.client.index(index).get_settings()
            index_tmp = await self.client.create_index(index_name_tmp, primary_key=pk)
            task = await index_tmp.update_settings(settings)
            logger.info(f"Waiting for update tmp index {index_name_tmp} settings to complete...")
            await self.client.wait_for_task(
                task_id=task.task_uid, timeout_in_ms=self.wait_for_task_timeout
            )
        else:
            logger.info("Not deleting index when refreshing data")
            index_name_tmp = index

        tasks = []
        count = 0
        async for items in data:
            task = await self.add_data(sync, items)
            tasks.append(task)
            count += len(items)
        wait_tasks = [
            self.client.wait_for_task(
                task_id=item.task_uid, timeout_in_ms=self.wait_for_task_timeout
            )
            for item in tasks
        ]
        logger.info(f"Waiting for insert tmp index {index_name_tmp} to complete...")
        await asyncio.gather(*wait_tasks)

        if not keep_index:
            task = await self.client.swap_indexes([(index, index_name_tmp)])
            logger.info(f"Waiting for swap index {index} to complete...")
            await self.client.wait_for_task(
                task_id=task.task_uid, timeout_in_ms=self.wait_for_task_timeout
            )
            await self.client.index(index_name_tmp).delete()
            logger.success(f"Swap index {index} complete")

        return count

    async def get_count(self, index: str):
        stats = await self.client.index(index).get_stats()
        return stats.number_of_documents

    async def index_exists(self, index: str):
        try:
            await self.client.get_index(index)
            return True
        except MeilisearchApiError as e:
            if e.code == "index_not_found":
                return False
            raise e

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
        task = None
        if event_type == EventType.create:
            task = await index.add_documents(
                [event.mapping_data(sync.fields) for event in events], primary_key=sync.pk
            )
        elif event_type == EventType.update:
            task = await index.update_documents(
                [event.mapping_data(sync.fields) for event in events], primary_key=sync.pk
            )
        elif event_type == EventType.delete:
            task = await index.delete_documents([str(event.data[sync.pk]) for event in events])
        for event in events:
            await self.handle_plugins_post(sync, event)
        return task

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
