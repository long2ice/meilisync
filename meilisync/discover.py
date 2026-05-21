import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Type

from meilisync import progress, source
from meilisync.enums import ProgressType, SourceType
from meilisync.progress import Progress
from meilisync.source import Source


def _discover(module: ModuleType, t: Type):
    ret = {}
    for m in pkgutil.iter_modules(module.__path__):
        try:
            mod = importlib.import_module(f"{module.__name__}.{m.name}")
        except ModuleNotFoundError:
            # Enables optional dependencies of sources and progress.
            continue
        for _, member in inspect.getmembers(mod, inspect.isclass):
            if issubclass(member, t) and member is not t:
                ret[member.type] = member
    return ret


_sources = _discover(source, Source)


def get_source(type_: SourceType) -> Type[Source]:
    return _sources[type_]  # type: ignore


_progress = _discover(progress, Progress)


def get_progress(type_: ProgressType) -> Type[Progress]:
    return _progress[type_]  # type: ignore
