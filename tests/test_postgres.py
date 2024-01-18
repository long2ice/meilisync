import time

import psycopg2

from conftest import client

index = client.index("postgres")


async def test_sync():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="123456",
        database="test",
    )
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS test")
    cur.execute("CREATE TABLE IF NOT EXISTS test (id INT PRIMARY KEY, age INT, data_json JSON)")
    cur.execute(
        "INSERT INTO test (id, age, data_json) VALUES (%s, %s, %s)",
        (1, 18, '{"name": "test data"}'),
    )
    conn.commit()
    time.sleep(2)
    ret = await index.get_documents()
    assert ret.results == [{"id": 1, "age": 18, "data_json": {"name": "test data"}}]
