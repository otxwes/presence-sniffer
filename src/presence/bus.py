"""Asyncio publish/subscribe event bus.

All sensors publish PresenceEvents; the aggregator folds them into
PresenceSnapshots on a second channel. Subscribers (OSC bridge, viz) never touch
sensors directly — that decoupling is what lets the same modules run on Mac-dev
and Pi-portable.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any


class EventBus:
    """Minimal async pub/sub. Handlers are awaited sequentially per event."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[[Any], Awaitable[None]]]] = defaultdict(list)

    def subscribe(self, channel: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        self._subs[channel].append(handler)

    async def publish(self, channel: str, payload: Any) -> None:
        for handler in list(self._subs.get(channel, ())):
            try:
                await handler(payload)
            except Exception:
                import logging
                logging.getLogger(__name__).exception("bus handler error on %s", channel)
