from typing import Any

import httpx

from providers.base import MediaProvider


class MangaLibClient(MediaProvider):
    name = "mangalib"

    def __init__(self, base_url: str = "https://mangalib.me") -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=15.0,
            http2=True,
            headers={"User-Agent": "anime_tracker_bot/1.0", "Accept": "application/json"},
        )

    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        response = await self.client.get(
            f"{self.base_url}/search",
            params={"type": "manga", "q": query},
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse(item, media_type) for item in data if isinstance(item, dict)]

    async def get_media(self, external_id: str, media_type: str) -> dict[str, Any] | None:
        response = await self.client.get(
            f"{self.base_url}/manga-short-info",
            params={"id": external_id, "type": media_type},
            headers={"Referer": f"{self.base_url}/"},
        )
        response.raise_for_status()
        item = response.json()
        if not isinstance(item, dict) or not item.get("id"):
            return None
        return self._parse(item, media_type)

    @staticmethod
    def _parse(item: dict[str, Any], media_type: str) -> dict[str, Any]:
        title = item.get("rus_name") or item.get("name") or item.get("eng_name") or "Без названия"
        aliases = [value.strip() for value in (item.get("otherNames") or "").split("/") if value.strip()]
        for value in [item.get("name"), item.get("eng_name")]:
            if value and value != title and value not in aliases:
                aliases.append(value)

        categories = item.get("categories") or []
        genres = [category.get("name") for category in categories if isinstance(category, dict) and category.get("name")]
        chapters = item.get("chapters")
        if isinstance(chapters, dict):
            chapters = chapters.get("count")

        cover_url = item.get("coverImage") or item.get("cover")
        if cover_url and not str(cover_url).startswith("http"):
            cover_url = None

        source_ids = {}
        if item.get("shiki_id"):
            source_ids["shikimori"] = str(item["shiki_id"])

        return {
            "provider": "mangalib",
            "provider_id": str(item.get("id")),
            "type": media_type,
            "title": title,
            "title_english": item.get("eng_name"),
            "title_original": item.get("name"),
            "title_variants": aliases,
            "image_url": cover_url,
            "score": float(item["rate_avg"]) if str(item.get("rate_avg", "")).replace(".", "", 1).isdigit() else None,
            "year": int(item["releaseDate"]) if str(item.get("releaseDate", "")).isdigit() else None,
            "status": (item.get("status") or {}).get("label") if isinstance(item.get("status"), dict) else None,
            "description": item.get("summary"),
            "genres": genres,
            "source_ids": source_ids,
            "url": item.get("href") or f"https://mangalib.me/{item.get('slug')}",
            "episodes": None,
            "chapters": chapters,
            "volumes": None,
        }

    async def close(self) -> None:
        await self.client.aclose()
