"""A module cited by the symbols fixture."""

THRESHOLD = 0.3
LIMIT: int = 10
LOW, HIGH = 0, 1

try:
    from json import dumps as optional_dumps
except ImportError:
    optional_dumps = None


def compute(value: float) -> bool:
    return value >= THRESHOLD


class Engine:
    name: str = "engine"

    class Config:
        retries = 3

    def run(self) -> None:
        return None

    async def stop(self) -> None:
        return None
