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
    cur.execute("CREATE TABLE IF NOT EXISTS test (id INT PRIMARY KEY, age INT)")
    cur.execute("INSERT INTO test (id, age) VALUES (%s, %s)", (1, 18))
    time.sleep(2)
    meili_data = await index.get_documents()
    assert meili_data == [
        {
            "id": 1,
            "age": 18,
        }
    ]
