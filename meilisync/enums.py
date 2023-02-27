from enum import Enum


class EventType(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"


class SourceType(str, Enum):
    mongo = "mongo"
    mysql = "mysql"
    postgres = "postgres"


class ProgressType(str, Enum):
    file = "file"
    redis = "redis"
