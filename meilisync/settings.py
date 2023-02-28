from typing import List, Optional

from pydantic import BaseModel, BaseSettings, Extra

from meilisync.enums import ProgressType, SourceType


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


class Sync(BaseModel):
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


class Settings(BaseSettings):
    progress: Progress
    debug: bool = False
    source: Source
    meilisearch: MeiliSearch
    sync: List[Sync]
    sentry: Optional[Sentry]

    @property
    def tables(self):
        return [sync.table for sync in self.sync]
