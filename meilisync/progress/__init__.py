from meilisync.enums import ProgressType


class Progress:
    type: ProgressType

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def set(self, **kwargs):
        raise NotImplementedError

    async def get(self):
        raise NotImplementedError
