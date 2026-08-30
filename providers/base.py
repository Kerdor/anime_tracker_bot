from abc import ABC, abstractmethod
from typing import Any


class MediaProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_media(self, external_id: str, media_type: str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def close(self) -> None:
        pass
