import asyncio

import motor

from conftest import client

index = client.index("mongo")


async def test_sync():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://root:root@mongo:27017")
    db = client.test
    collection = db.test
    data = {
        "id": 1,
        "age": 18,
    }
    await collection.insert_one(data)
    await asyncio.sleep(2)
    meili_data = await index.get_documents()
    assert meili_data == [data]
