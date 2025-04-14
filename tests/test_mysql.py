import asyncio
from pathlib import Path

from meilisync.main import load


async def test_sync():
    meili, source, *_ = await load(config_file=Path(__file__).parent / 'config/mysql.yml')
    conn = await source.get_connection()
    index_name = 'mysql'
    await meili.client.delete_index_if_exists(index_name)
    await meili.client.create_index(index_name)

    async with conn.cursor() as cur:
        await cur.execute("DROP TABLE IF EXISTS test")
        await cur.execute(
            "CREATE TABLE IF NOT EXISTS test (id INT PRIMARY KEY, age INT, time timestamp NOT NULL)"
        )
        await cur.execute(
            "INSERT INTO test (id, age, time) VALUES (%s, %s, %s)",
            (1, 46, "1977-01-27 22:00:53"),
        )
        await conn.commit()
    await asyncio.sleep(2)
    ret = await meili.client.index(index_name).get_documents()
    assert ret.results == [{"id": 1, "age": 46, "time": 223250453}]
