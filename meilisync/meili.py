import asyncio
from typing import AsyncGenerator, List, Optional, Type, Union

from loguru import logger
from meilisearch_python_async import Client
from meilisearch_python_async.errors import MeilisearchApiError
from meilisearch_python_async.task import wait_for_task

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
        self.client = Client(
            api_url,
            api_key,
        )
        self.plugins = plugins or []
        self.wait_for_task_timeout = wait_for_task_timeout

    async def add_full_data(self, index: str, pk: str, data: AsyncGenerator):
        tasks = []
        async for items in data:
            task = await self.client.index(index).add_documents(items, primary_key=pk)
            tasks.append(task)
        return tasks

    async def refresh_data(self, index: str, pk: str, data: AsyncGenerator):
        index_name_tmp = f"{index}_tmp"
        try:
            await self.client.index(index_name_tmp).delete()
        except MeilisearchApiError as e:
            if e.code != "MeilisearchApiError.index_not_found":
                raise
        settings = await self.client.index(index).get_settings()
        index_tmp = await self.client.create_index(index_name_tmp, primary_key=pk)
        task = await index_tmp.update_settings(settings)
        logger.info(f"Waiting for update tmp index {index_name_tmp} settings to complete...")
        await wait_for_task(
            client=self.client, task_id=task.task_uid, timeout_in_ms=self.wait_for_task_timeout
        )
        tasks = []
        count = 0
        async for items in data:
            count += len(items)
            tasks.extend(await self.add_full_data(index_name_tmp, pk, items))
        wait_tasks = [
            wait_for_task(
                client=self.client, task_id=item.task_uid, timeout_in_ms=self.wait_for_task_timeout
            )
            for item in tasks
        ]
        logger.info(f"Waiting for insert tmp index {index_name_tmp} to complete...")
        await asyncio.gather(*wait_tasks)
        task = await self.client.swap_indexes([(index, index_name_tmp)])
        logger.info("Waiting for swap index to complete...")
        await wait_for_task(
            client=self.client, task_id=task.task_uid, timeout_in_ms=self.wait_for_task_timeout
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
