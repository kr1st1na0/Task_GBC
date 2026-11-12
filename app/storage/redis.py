from app.config import REDIS_URL

from typing import Any
import json
import redis.asyncio as redis

_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _key(job_id: str) -> str:
    return f"job:{job_id}"

async def create_job(job_id: str) -> None:
    await _client.hset(
        _key(job_id),
        mapping = {
            "status": "pending",
            "total": 0,
            "processed": 0,
            "failed": 0,
        },
    )
    await _client.set(f"{_key(job_id)}:result", json.dumps(None))
    await _client.set(f"{_key(job_id)}:processed_orders", json.dumps([]))
    await _client.set(f"{_key(job_id)}:all_seen_ids", json.dumps([]))


async def get_job(job_id: str) -> dict[str, Any] | None:
    key = _key(job_id)
    if not await _client.exists(key):
        return None

    data = await _client.hgetall(key)
    result_raw = await _client.get(f"{key}:result")
    processed_orders_raw = await _client.get(f"{key}:processed_orders")
    all_seen_raw = await _client.get(f"{key}:all_seen_ids")

    return {
        "status": data.get("status"),
        "total": int(data.get("total", 0)),
        "processed": int(data.get("processed", 0)),
        "failed": int(data.get("failed", 0)),
        "result": json.loads(result_raw) if result_raw else None,
        "processed_orders": json.loads(processed_orders_raw) if processed_orders_raw else [],
        "all_seen_ids": json.loads(all_seen_raw) if all_seen_raw else [],
    }


async def update_job(job_id: str, **fields: Any) -> None:
    key = _key(job_id)
    if not await _client.exists(key):
        return
    hash_fields = {}
    for name, value in fields.items():
        if name == "result":
            await _client.set(f"{key}:result", json.dumps(value))
        elif name == "processed_orders":
            await _client.set(f"{key}:processed_orders", json.dumps(value))
        elif name == "all_seen_ids":
            await _client.set(f"{key}:all_seen_ids", json.dumps(list(value)))
        else:
            hash_fields[name] = value
    if hash_fields:
        await _client.hset(key, mapping=hash_fields)
