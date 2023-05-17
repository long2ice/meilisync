import datetime
from typing import Optional

from pydantic import BaseModel

from meilisync.enums import EventType


class ProgressEvent(BaseModel):
    progress: dict


class Event(ProgressEvent):
    type: EventType
    table: str
    data: dict

    def mapping_data(self, fields_mapping: Optional[dict] = None):
        data = {}
        for k, v in self.data.items():
            if isinstance(v, datetime.datetime):
                v = int(v.timestamp())

            if (fields_mapping is not None) and k in fields_mapping:
                data[fields_mapping[k]] = v
            else:
                data[k] = v

        return data or self.data
