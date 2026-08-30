from typing import Any

import httpx

from providers.base import MediaProvider


class ShikimoriClient(MediaProvider):
    name = "shikimori"

    def __init__(self, base_url: str = "https://shikimori.one/api") -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "anime_tracker_bot/1.0"},
        )

    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        endpoint = "animes" if media_type == "anime" else "mangas"
        response = await self.client.get(f"{self.base_url}/{endpoint}", params={"search": query, "limit": 20})
        response.raise_for_status()
        return [self._parse(item, media_type) for item in response.json()]

    async def get_media(self, external_id: str, media_type: str) -> dict[str, Any] | None:
        endpoint = "animes" if media_type == "anime" else "mangas"
        response = await self.client.get(f"{self.base_url}/{endpoint}/{external_id}")
        response.raise_for_status()
        return self._parse(response.json(), media_type)

    @staticmethod
    def _parse(item: dict[str, Any], media_type: str) -> dict[str, Any]:
        russian = item.get("russian")
        name = item.get("name") or russian or "Без названия"
        aliases = [value for value in [russian, item.get("name")] if value and value != (russian or name)]
        source_ids = {"shikimori": str(item.get("id"))} if item.get("id") is not None else {}
        if item.get("mal_id") is not None:
            source_ids["mal"] = str(item["mal_id"])

        return {
            "provider": "shikimori",
            "provider_id": str(item.get("id")),
            "source_ids": source_ids,
            "type": media_type,
            "title": russian or name,
            "title_english": name,
            "title_original": name,
            "title_variants": aliases,
            "image_url": ((item.get("image") or {}).get("original") or None),
            "score": float(item["score"]) if item.get("score") else None,
            "year": int(item["aired_on"][:4]) if media_type == "anime" and item.get("aired_on", "")[:4].isdigit() else None,
            "description": item.get("description"),
            "genres": [genre.get("russian") or genre.get("name") for genre in item.get("genres", [])],
            "url": f"https://shikimori.one/{'animes' if media_type == 'anime' else 'mangas'}/{item.get('id')}",
            "episodes": item.get("episodes"),
            "chapters": item.get("chapters"),
            "volumes": item.get("volumes"),
        }

    async def close(self) -> None:
        await self.client.aclose()
