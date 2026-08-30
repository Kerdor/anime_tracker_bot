from typing import Any

import httpx

from config import settings


class JikanClient:
    def __init__(self) -> None:
        self.base_url = settings.jikan_base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=15.0)

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self.client.get(f"{self.base_url}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _parse_media(item: dict[str, Any], media_type: str) -> dict[str, Any]:
        aired = item.get("aired") or {}
        published = item.get("published") or {}
        prop = aired.get("prop") or {}
        from_date = prop.get("from") or {}
        year = item.get("year") or from_date.get("year") or published.get("from", "")[:4]

        titles = item.get("titles") or []
        title_variants = [title.get("title") for title in titles if title.get("title")]

        return {
            "mal_id": item["mal_id"],
            "title": item.get("title") or item.get("title_english") or "Без названия",
            "title_english": item.get("title_english"),
            "title_original": item.get("title_japanese"),
            "title_variants": title_variants,
            "image_url": (item.get("images") or {}).get("jpg", {}).get("large_image_url")
            or (item.get("images") or {}).get("jpg", {}).get("image_url"),
            "score": item.get("score"),
            "year": int(year) if str(year).isdigit() else None,
            "status": item.get("status"),
            "type": media_type,
            "description": item.get("synopsis"),
            "genres": [genre.get("name") for genre in item.get("genres", []) if genre.get("name")],
            "url": item.get("url"),
            "episodes": item.get("episodes"),
            "chapters": item.get("chapters"),
            "volumes": item.get("volumes"),
            "studios": [studio.get("name") for studio in item.get("studios", []) if studio.get("name")],
            "authors": [author.get("name") for author in item.get("authors", []) if author.get("name")],
        }

    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        endpoint = "anime" if media_type == "anime" else "manga"
        data = await self._get(endpoint, {"q": query, "limit": 25, "sfw": True})
        return [self._parse_media(item, media_type) for item in data.get("data", [])]

    async def get_media(self, mal_id: int, media_type: str) -> dict[str, Any]:
        endpoint = "anime" if media_type == "anime" else "manga"
        data = await self._get(f"{endpoint}/{mal_id}/full")
        return self._parse_media(data.get("data", {}), media_type)

    async def close(self) -> None:
        await self.client.aclose()
