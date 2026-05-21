import asyncio
from typing import List, Optional

import typer
import yaml
from loguru import logger

from meilisync.discover import get_progress, get_source
from meilisync.event import EventCollection
from meilisync.meili import Meili
from meilisync.schemas import Event
from meilisync.settings import Settings
from meilisync.version import __VERSION__

app = typer.Typer()


@app.callback()
def callback(
    context: typer.Context,
    config_file: str = typer.Option(
        "config.yml",
        "-c",
        "--config",
        help="Config file path",
    ),
):
    async def _():
        if context.invoked_subcommand == "version":
            return
        context.ensure_object(dict)
        with open(config_file) as f:
            config = f.read()
        settings = Settings.model_validate(yaml.safe_load(config))
        if settings.debug:
            logger.debug(settings)
        if settings.sentry:
            sentry = settings.sentry

            import sentry_sdk

            sentry_sdk.init(
                dsn=sentry.dsn,
                environment=sentry.environment,
            )
        progress = get_progress(settings.progress.type)(
            **settings.progress.model_dump(exclude={"type"})
        )
        current_progress = await progress.get()
        source = get_source(settings.source.type)(
            progress=current_progress,
            tables=settings.tables,
            **settings.source.model_dump(exclude={"type"}),
        )
        meilisearch = settings.meilisearch
        meili = Meili(meilisearch.api_url, meilisearch.api_key, settings.plugins_cls())
        context.obj["current_progress"] = current_progress
        context.obj["source"] = source
        context.obj["meili"] = meili
        context.obj["settings"] = settings
        context.obj["progress"] = progress

    asyncio.run(_())


@app.command(help="Show meilisync version")
def version():
    typer.echo(__VERSION__)


@app.command(help="Start meilisync")
def start(
    context: typer.Context,
):
    current_progress = context.obj["current_progress"]
    source = context.obj["source"]
    meili = context.obj["meili"]
    settings = context.obj["settings"]
    progress = context.obj["progress"]
    meili_settings = settings.meilisearch
    collection = EventCollection()
    lock = None

    async def _():
        nonlocal current_progress
        for sync in settings.sync:
            if sync.full and not await meili.index_exists(sync.index_name):
                count = 0
                async for items in source.get_full_data(sync, meili_settings.insert_size or 10000):
                    count += len(items)
                    await meili.add_data(sync, items)
                if count:
                    logger.info(
                        f'Full data sync for table "{settings.source.database}.{sync.table}" '
                        f"done! {count} documents added."
                    )
                else:
                    logger.info(
                        f'No data found for table "{settings.source.database}.{sync.table}".'
                    )
        logger.info(f'Start increment sync data from "{settings.source.type}" to MeiliSearch...')
        async for event in source:
            if settings.debug:
                logger.debug(event)
            current_progress = event.progress
            if isinstance(event, Event):
                sync = settings.get_sync(event.table)
                if not sync:
                    continue
                if not meili_settings.insert_size and not meili_settings.insert_interval:
                    await meili.handle_event(event, sync)
                    await progress.set(**current_progress)
                else:
                    collection.add_event(sync, event)
                    if collection.size >= meili_settings.insert_size:
                        async with lock:
                            await meili.handle_events(collection)
                            await progress.set(**current_progress)
            else:
                await progress.set(**current_progress)

    async def interval():
        if not settings.meilisearch.insert_interval:
            return
        while True:
            await asyncio.sleep(settings.meilisearch.insert_interval)
            try:
                async with lock:
                    await meili.handle_events(collection)
                    await progress.set(**current_progress)
            except Exception as e:
                logger.exception(e)
                logger.error(f"Error when insert data to MeiliSearch: {e}")

    async def run():
        nonlocal lock
        lock = asyncio.Lock()
        await asyncio.gather(_(), interval())

    asyncio.run(run())


@app.command(help="Refresh all data by swap index")
def refresh(
    context: typer.Context,
    table: Optional[List[str]] = typer.Option(
        None, "-t", "--table", help="Table name, if not set, all tables"
    ),
    size: int = typer.Option(
        10000, "-s", "--size", help="Size of data for each insert to be inserted into MeiliSearch"
    ),
    keep_index: bool = typer.Option(
        False,
        "-d",
        "--keep-index",
        help="Flag to avoid deleting the existing index before doing a full sync.",
    ),
):
    async def _():
        settings = context.obj["settings"]
        source = context.obj["source"]
        meili = context.obj["meili"]
        progress = context.obj["progress"]
        for sync in settings.sync:
            if not table or sync.table in table:
                current_progress = await source.get_current_progress()
                await progress.set(**current_progress)
                count = await meili.refresh_data(
                    sync,
                    source.get_full_data(sync, size),
                    keep_index,
                )
                if count:
                    logger.info(
                        f'Full data sync for table "{settings.source.database}.{sync.table}" '
                        f"done! {count} documents added."
                    )
                else:
                    logger.info(
                        f'No data found for table "{settings.source.database}.{sync.table}".'
                    )

    asyncio.run(_())


@app.command(
    help="Check whether the data in the database is consistent with the data in MeiliSearch"
)
def check(
    context: typer.Context,
    table: Optional[List[str]] = typer.Option(
        None, "-t", "--table", help="Table name, if not set, all tables"
    ),
):
    async def _():
        settings = context.obj["settings"]
        source = context.obj["source"]
        meili = context.obj["meili"]
        for sync in settings.sync:
            if not table or sync.table in table:
                count = await source.get_count(sync)
                meili_count = await meili.get_count(sync.index_name)
                if count == meili_count:
                    logger.info(
                        f'Table "{settings.source.database}.{sync.table}" '
                        f"is consistent with MeiliSearch, count: {count}."
                    )
                else:
                    logger.error(
                        f'Table "{settings.source.database}.{sync.table}" is inconsistent '
                        f"with MeiliSearch, Database count: {count}, "
                        f'MeiliSearch count: {meili_count}."'
                    )

    asyncio.run(_())


if __name__ == "__main__":
    app()
