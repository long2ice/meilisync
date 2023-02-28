import asyncio
import sys

import yaml
from loguru import logger

from meilisync.discover import get_progress, get_source
from meilisync.meili import Meili
from meilisync.schemas import Event
from meilisync.settings import Settings


async def cli():
    if len(sys.argv) == 2:
        config_file = sys.argv[1]
    else:
        config_file = "config.yml"
    with open(config_file) as f:
        config = f.read()
    settings = Settings.parse_obj(yaml.safe_load(config))
    if settings.sentry:
        sentry = settings.sentry

        import sentry_sdk

        sentry_sdk.init(
            dsn=sentry.dsn,
            environment=sentry.environment,
        )
    progress = get_progress(settings.progress.type)(**settings.progress.dict(exclude={"type"}))
    current_progress = await progress.get()
    source = get_source(settings.source.type)(
        progress=current_progress,
        tables=settings.tables,
        **settings.source.dict(exclude={"type"}),
    )
    meili = Meili(settings.debug, settings.meilisearch, settings.sync)
    if not current_progress:
        for sync in settings.sync:
            if sync.full:
                data = await source.get_full_data(sync)
                if data:
                    await meili.add_full_data(sync.index_name, sync.pk, data)
                    logger.info(
                        f'Full data sync for table "{settings.source.database}.{sync.table}" '
                        f"done! {len(data)} documents added."
                    )
                else:
                    logger.info(
                        f'Full data sync for table "{settings.source.database}.{sync.table}" '
                        f"done! No data found."
                    )
    logger.info(f'Start increment sync data from "{settings.source.type}" to MeiliSearch...')
    async for event in source:
        if isinstance(event, Event):
            await meili.handle_event(event)
        await progress.set(**event.progress)


def main():
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        logger.info("Bye!")


if __name__ == "__main__":
    main()
