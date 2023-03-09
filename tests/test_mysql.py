import asyncio

import asyncmy

from conftest import client

index = client.index("mysql")


async def test_sync():
    conn = await asyncmy.connect(
        host="localhost",
        user="root",
        password="123456",
        port=3306,
        database="test",
    )
    await conn.execute("CREATE TABLE IF NOT EXISTS test (id INT PRIMARY KEY, age INT)")
    await conn.execute("INSERT INTO test (id, age) VALUES (%s, %s)", (1, 18))
    await asyncio.sleep(2)
    meili_data = await index.get_documents()
    assert meili_data == [
        {
            "id": 1,
            "age": 18,
        }
    ]
