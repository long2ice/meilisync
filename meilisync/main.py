import asyncio
from typing import List, Optional

import typer
import yaml
from loguru import logger

from meilisync.discover import get_progress, get_source
from meilisync.meili import Meili
from meilisync.schemas import Event
from meilisync.settings import Settings

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
        context.ensure_object(dict)
        with open(config_file) as f:
            config = f.read()
        settings = Settings.parse_obj(yaml.safe_load(config))
        if settings.debug:
            logger.debug(settings)
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
        meilisearch = settings.meilisearch
        meili = Meili(
            settings.debug, meilisearch.api_url, meilisearch.api_key, settings.plugins_cls()
        )
        context.obj["current_progress"] = current_progress
        context.obj["source"] = source
        context.obj["meili"] = meili
        context.obj["settings"] = settings
        context.obj["progress"] = progress

    asyncio.run(_())


@app.command(help="Start meilisync")
def start(
    context: typer.Context,
):
    async def _():
        current_progress = context.obj["current_progress"]
        source = context.obj["source"]
        meili = context.obj["meili"]
        settings = context.obj["settings"]
        progress = context.obj["progress"]
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
                            f'No data found for table "{settings.source.database}.{sync.table}".'
                        )
        logger.info(f'Start increment sync data from "{settings.source.type}" to MeiliSearch...')
        async for event in source:
            if isinstance(event, Event):
                sync = settings.get_sync(event.table)
                if sync:
                    await meili.handle_event(event, sync)
            await progress.set(**event.progress)

    asyncio.run(_())


@app.command(help="Delete all data in MeiliSearch and full sync")
def refresh(
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
                await meili.delete_all_data(sync.index_name)
                data = await source.get_full_data(sync)
                if data:
                    await meili.add_full_data(sync.index_name, sync.pk, data)
                    logger.info(
                        f'Full data sync for table "{settings.source.database}.{sync.table}" '
                        f"done! {len(data)} documents added."
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
