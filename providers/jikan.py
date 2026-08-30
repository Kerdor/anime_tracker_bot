from typing import Any

import httpx

from config import settings


class JikanClient:
    def __init__(self) -> None:
        self.base_url = settings.jikan_base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=15.0)

    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        endpoint = "anime" if media_type == "anime" else "manga"
        response = await self.client.get(
            f"{self.base_url}/{endpoint}",
            params={"q": query, "limit": 10, "sfw": True},
        )
        response.raise_for_status()
        data = response.json().get("data", [])

        return [
            {
                "mal_id": item["mal_id"],
                "title": item.get("title") or item.get("title_english") or "Без названия",
                "title_original": item.get("title_japanese"),
                "image_url": (item.get("images") or {}).get("jpg", {}).get("image_url"),
                "score": item.get("score"),
                "year": item.get("year") or item.get("aired", {}).get("prop", {}).get("from", {}).get("year"),
                "status": item.get("status"),
                "type": media_type,
            }
            for item in data
        ]

    async def close(self) -> None:
        await self.client.aclose()
