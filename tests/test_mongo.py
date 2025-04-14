import asyncio
from pathlib import Path

from meilisync.main import load


async def test_sync():
    meili, source, *_ = await load(config_file=Path(__file__).parent / 'config/mongo.yml')
    index_name = 'mongo'
    await meili.client.delete_index_if_exists(index_name)
    await meili.client.create_index(index_name)

    db = source.db
    collection = db['test']
    await collection.delete_many({})
    data = {
        "age": 18,
    }
    inserted_id = (await collection.insert_one(data)).inserted_id
    await asyncio.sleep(2)
    ret = await meili.client.index(index_name).get_documents()
    assert ret.results == [
        {
            "age": 18,
            "_id": str(inserted_id),
        }
    ]
