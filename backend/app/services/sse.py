from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import structlog

log = structlog.get_logger()


class EventBus:
    async def publish(self, event_id: str, payload: dict[str, Any]) -> None: ...
    async def subscribe(self, event_id: str):
        yield  # pragma: no cover


class MemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self.history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def publish(self, event_id: str, payload: dict[str, Any]) -> None:
        self.history[event_id].append(payload)
        for q in list(self._subs.get(event_id, [])):
            await q.put(payload)

    async def subscribe(self, event_id: str):
        q: asyncio.Queue = asyncio.Queue()
        self._subs[event_id].append(q)
        try:
            for past in self.history.get(event_id, []):
                yield past
            while True:
                item = await q.get()
                yield item
        finally:
            self._subs[event_id].remove(q)


class RedisEventBus(EventBus):
    def __init__(self, redis) -> None:
        self.redis = redis

    def _channel(self, event_id: str) -> str:
        return f"eventos:sse:{event_id}"

    async def publish(self, event_id: str, payload: dict[str, Any]) -> None:
        await self.redis.publish(self._channel(event_id), json.dumps(payload))
        await self.redis.rpush(f"eventos:sse:hist:{event_id}", json.dumps(payload))
        await self.redis.ltrim(f"eventos:sse:hist:{event_id}", -100, -1)

    async def subscribe(self, event_id: str):
        hist = await self.redis.lrange(f"eventos:sse:hist:{event_id}", 0, -1)
        for raw in hist:
            yield json.loads(raw)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._channel(event_id))
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode()
                yield json.loads(data)
        finally:
            await pubsub.unsubscribe(self._channel(event_id))
            await pubsub.close()


memory_bus = MemoryEventBus()
