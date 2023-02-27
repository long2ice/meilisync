from typing import List

from meilisync.enums import SourceType
from meilisync.settings import Sync


class Source:
    type: SourceType

    def __init__(
        self,
        progress: dict,
        tables: List[str],
        **kwargs,
    ):
        self.kwargs = kwargs
        self.tables = tables
        self.progress = progress

    async def __aiter__(self):
        raise NotImplementedError

    async def get_full_data(self, sync: Sync):
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError
