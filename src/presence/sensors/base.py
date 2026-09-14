"""Sensor adapters share this pulse interface; the aggregator pushes their outputs onto the bus."""


class BaseSensor:
    source = "base"

    def __init__(self, bus) -> None:
        self.bus = bus

    async def run(self) -> None:  # pragma: no cover - hardware adapters override
        raise NotImplementedError(f"{type(self).__name__} is a Phase 1 stub")
