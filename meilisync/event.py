from meilisync.enums import EventType
from meilisync.schemas import Event
from meilisync.settings import Sync


class EventCollection:
    def __init__(self):
        self._size = 0
        self._events = {}

    def add_event(self, sync: Sync, event: Event):
        pk = event.data[sync.pk]
        self._events.setdefault(sync, {})
        self._events[sync][pk] = event

    @property
    def size(self):
        return self._size

    @property
    def pop_events(self):
        updated_events = {}
        created_events = {}
        deleted_events = {}
        for sync, events in self._events.items():
            updated_events[sync] = []
            created_events[sync] = []
            deleted_events[sync] = []
            for event in events.values():
                if event.type == EventType.create:
                    created_events[sync].append(event)
                elif event.type == EventType.update:
                    updated_events[sync].append(event)
                elif event.type == EventType.delete:
                    deleted_events[sync].append(event)
        self._events = {}
        self._size = 0
        return created_events, updated_events, deleted_events
