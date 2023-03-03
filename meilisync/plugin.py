import importlib

from loguru import logger

from meilisync.schemas import Event


class Plugin:
    is_global = False

    async def pre_event(self, event: Event):
        logger.debug(f"pre_event: {event}, is_global: {self.is_global}")
        return event

    async def post_event(self, event: Event):
        logger.debug(f"post_event: {event}, is_global: {self.is_global}")
        return event


def load_plugin(module_str: str):
    module, _, class_name = module_str.rpartition(".")
    return getattr(importlib.import_module(module), class_name)
