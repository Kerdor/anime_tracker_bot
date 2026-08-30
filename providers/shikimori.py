from typing import Any

import httpx


class ShikimoriClient:
    def __init__(self, base_url: str = "https://shikimori.one/api") -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "anime_tracker_bot/1.0"})

    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        endpoint = "animes" if media_type == "anime" else "mangas"
        response = await self.client.get(f"{self.base_url}/{endpoint}", params={"search": query, "limit": 20})
        response.raise_for_status()
        data = response.json()
        return [self._parse(item, media_type) for item in data]

    @staticmethod
    def _parse(item: dict[str, Any], media_type: str) -> dict[str, Any]:
        russian = item.get("russian")
        name = item.get("name") or russian or "Без названия"
        aliases = [value for value in [russian, item.get("name")] if value and value != name]
        return {
            "provider": "shikimori",
            "provider_id": str(item.get("id")),
            "mal_id": item.get("mal_id"),
            "type": media_type,
            "title": russian or name,
            "title_english": name,
            "title_original": name,
            "title_variants": aliases,
            "image_url": ((item.get("image") or {}).get("original") or None),
            "score": float(item["score"]) if item.get("score") else None,
            "year": item.get("aired_on", "")[:4] if media_type == "anime" and item.get("aired_on") else None,
            "description": item.get("description"),
            "genres": [genre.get("russian") or genre.get("name") for genre in item.get("genres", [])],
            "url": f"https://shikimori.one/{'animes' if media_type == 'anime' else 'mangas'}/{item.get('id')}",
            "episodes": item.get("episodes"),
            "chapters": item.get("chapters"),
            "volumes": item.get("volumes"),
        }

    async def close(self) -> None:
        await self.client.aclose()
