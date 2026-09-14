"""Aggregator daemon: sensory input -> bus -> normalized PresenceSnapshot stream.

Usage:
    python -m presence.aggregator --simulator --print
"""
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
from typing import Optional

from .bus import EventBus
from .events import PresenceEvent, PresenceSnapshot
from .osc_bridge import OscBridge
from .simulator import DeviceSimulator

SNAPSHOT_INTERVAL = 0.5  # seconds; feeds audio/viz at 2 Hz


class Aggregator:
    """Folds a stream of PresenceEvents into PresenceSnapshots and publishes them."""

    WINDOW_SECONDS = 6.0  # presence window for density/churn

    def __init__(self, bus: EventBus, print_events: bool = False) -> None:
        self.bus = bus
        self.print_events = print_events
        self._seen: dict[str, PresenceEvent] = {}
        self._arrivals: list[float] = []
        self._latest: PresenceSnapshot = PresenceSnapshot()

    async def on_event(self, event: PresenceEvent) -> None:
        prev = self._seen.get(event.device_id)
        if prev is None:
            self._arrivals.append(event.ts)
        self._seen[event.device_id] = event  # keep strongest/latest observation
        if self.print_events:
            print(f"[event] {event.device_class:12s} rssi={event.rssi:6.1f} "
                  f"prox={event.proximity:4.2f} id={event.device_id}", file=sys.stderr)

    def _make_snapshot(self) -> PresenceSnapshot:
        now = time.time()
        events = [e for e in self._seen.values() if now - e.ts <= self.WINDOW_SECONDS]
        self._seen = {e.device_id: e for e in events}
        self._arrivals = [t for t in self._arrivals if now - t <= self.WINDOW_SECONDS]

        density = len(events)
        churn = len(self._arrivals) / self.WINDOW_SECONDS
        proximity = max((e.proximity for e in events), default=0.0)
        wifi = sum(1 for e in events if e.band in ("2.4g", "5g"))
        ble = sum(1 for e in events if e.band == "ble")
        band_balance = 0.0 if (wifi + ble) == 0 else (ble - wifi) / (wifi + ble)
        by_class: dict[str, int] = {}
        for e in events:
            by_class[e.device_class] = by_class.get(e.device_class, 0) + 1

        return PresenceSnapshot(
            ts=now, density=density, churn=churn, proximity=proximity,
            band_balance=band_balance, rf_warmth=0.0, by_class=by_class,
        )

    async def snapshot_loop(self) -> None:
        while True:
            await asyncio.sleep(SNAPSHOT_INTERVAL)
            self._latest = self._make_snapshot()
            await self.bus.publish("snapshot", self._latest)
            if self.print_events:
                d = self._latest.to_dict()
                print(f"[snapshot] density={d['density']} churn={d['churn']} "
                      f"prox={d['proximity']} warmth={d['rf_warmth']}",
                      file=sys.stderr)


async def main() -> None:
    parser = argparse.ArgumentParser(description="presence-sniffer aggregator")
    parser.add_argument("--simulator", action="store_true", help="use built-in device simulator")
    parser.add_argument("--print", dest="print_events", action="store_true")
    parser.add_argument("--osc-host", default="127.0.0.1")
    parser.add_argument("--osc-port", type=int, default=9090)
    args = parser.parse_args()

    logging_setup()
    bus = EventBus()
    aggregator = Aggregator(bus, print_events=args.print_events)
    osc = OscBridge(host=args.osc_host, port=args.osc_port)
    bus.subscribe("event", aggregator.on_event)
    bus.subscribe("snapshot", osc.on_snapshot)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    print("aggregator: bus up, OSC -> "
          f"{args.osc_host}:{args.osc_port} (Ctrl-C to stop)", file=sys.stderr)

    tasks: list[asyncio.Task] = [asyncio.create_task(aggregator.snapshot_loop())]

    if args.simulator:
        sim = DeviceSimulator(seed=None)

        async def pump() -> None:
            async for batch in sim.events():
                for ev in batch:
                    await bus.publish("event", ev)

        tasks.append(asyncio.create_task(pump()))
        print("aggregator: simulator running", file=sys.stderr)
    else:
        print("aggregator: no sensor wired yet - run with --simulator", file=sys.stderr)

    await stop.wait()
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            print(f"task error: {exc!r}", file=sys.stderr)
        else:
            pass


def logging_setup() -> None:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


if __name__ == "__main__":
    asyncio.run(main())
