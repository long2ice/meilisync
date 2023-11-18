from typing import List

from pydantic import BaseModel, Extra
from pydantic_settings import BaseSettings

from meilisync.enums import ProgressType, SourceType
from meilisync.plugin import load_plugin


class Source(BaseModel):
    type: SourceType
    database: str

    class Config:
        extra = Extra.allow


class MeiliSearch(BaseModel):
    api_url: str
    api_key: str | None = None
    insert_size: int | None = None
    insert_interval: int | None = None


class BasePlugin(BaseModel):
    plugins: List[str] = []

    def plugins_cls(self):
        plugins = []
        for plugin in self.plugins or []:
            p = load_plugin(plugin)
            if p.is_global:
                plugins.append(p())
            else:
                plugins.append(p)
        return plugins


class Sync(BasePlugin):
    table: str
    pk: str = "id"
    full: bool = False
    index: str | None = None
    fields: dict | None = None

    @property
    def index_name(self):
        return self.index or self.table

    def __hash__(self):
        return hash(self.table)


class Progress(BaseModel):
    type: ProgressType

    class Config:
        extra = Extra.allow


class Sentry(BaseModel):
    dsn: str
    environment: str = "production"


class Settings(BaseSettings, BasePlugin):
    progress: Progress
    debug: bool = False
    source: Source
    meilisearch: MeiliSearch
    sync: List[Sync]
    sentry: Sentry | None = None

    @property
    def tables(self):
        return [sync.table for sync in self.sync]

    def get_sync(self, table: str):
        for sync in self.sync:
            if sync.table == table:
                return sync
