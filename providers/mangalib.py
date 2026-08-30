from typing import Any

import httpx

from providers.base import MediaProvider


class MangaLibClient(MediaProvider):
    name = "mangalib"

    def __init__(self, base_url: str = "https://mangalib.me") -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=15.0, http2=True, headers={"User-Agent": "anime_tracker_bot/1.0"})

    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        response = await self.client.get(
            f"{self.base_url}/search",
            params={"type": "manga", "q": query},
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse(item, media_type) for item in data if isinstance(item, dict)]

    async def get_media(self, external_id: str, media_type: str) -> dict[str, Any] | None:
        return None

    @staticmethod
    def _parse(item: dict[str, Any], media_type: str) -> dict[str, Any]:
        title = item.get("rus_name") or item.get("name") or item.get("eng_name") or "Без названия"
        aliases = [value.strip() for value in (item.get("otherNames") or "").split("/") if value.strip()]
        for value in [item.get("name"), item.get("eng_name")]:
            if value and value != title and value not in aliases:
                aliases.append(value)

        return {
            "provider": "mangalib",
            "provider_id": str(item.get("id")),
            "mal_id": None,
            "type": media_type,
            "title": title,
            "title_english": item.get("eng_name"),
            "title_original": item.get("name"),
            "title_variants": aliases,
            "image_url": item.get("cover"),
            "score": None,
            "year": int(item["releaseDate"]) if str(item.get("releaseDate", "")).isdigit() else None,
            "description": item.get("summary"),
            "genres": [],
            "url": f"https://mangalib.me/{item.get('slug')}",
            "episodes": None,
            "chapters": None,
            "volumes": None,
        }

    async def close(self) -> None:
        await self.client.aclose()
