from pydantic import BaseModel

from meilisync.enums import EventType


class ProgressEvent(BaseModel):
    progress: dict


class Event(ProgressEvent):
    type: EventType
    table: str
    data: dict

    def mapping_data(self, fields_mapping: dict):
        if not fields_mapping:
            return self.data
        data = {}
        for k, v in self.data.items():
            if k in fields_mapping:
                data[fields_mapping[k] or k] = v
        return data or self.data
