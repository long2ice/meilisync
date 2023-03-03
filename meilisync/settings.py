from typing import List, Optional

from pydantic import BaseModel, BaseSettings, Extra

from meilisync.enums import ProgressType, SourceType
from meilisync.plugin import load_plugin


class Source(BaseModel):
    type: SourceType
    host: str
    port: int
    database: str

    class Config:
        extra = Extra.allow


class MeiliSearch(BaseModel):
    api_url: str
    api_key: Optional[str]


class BasePlugin(BaseModel):
    plugins: Optional[List[str]]

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
    index: Optional[str]
    fields: Optional[dict]

    @property
    def index_name(self):
        return self.index or self.table


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
    sentry: Optional[Sentry]

    @property
    def tables(self):
        return [sync.table for sync in self.sync]
