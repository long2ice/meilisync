from pathlib import Path
import time
from meilisync.main import load

async def test_sync():
    meili, source, *_ = await load(config_file=Path(__file__).parent / 'config/postgres.yml')
    conn = source.conn
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS test")
    index_name = 'postgres'
    await meili.client.delete_index_if_exists(index_name)
    await meili.client.create_index(index_name)
    cur.execute("CREATE TABLE IF NOT EXISTS test (id INT PRIMARY KEY, age INT, data_json JSON)")
    cur.execute("INSERT INTO test (id, age, data_json) VALUES (%s, %s, %s)",(1, 18, '{"name": "test data"}'),)
    conn.commit()
    time.sleep(2)
    ret = await meili.client.index(index_name).get_documents()
    assert ret.results == [{"id": 1, "age": 18, "data_json": {"name": "test data"}}]
