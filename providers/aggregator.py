import asyncio
import re
from typing import Any

from providers.base import MediaProvider
from providers.jikan import JikanClient


class MediaAggregator:
    def __init__(self, providers: list[MediaProvider] | None = None) -> None:
        self.providers = providers or [JikanClient()]

    @staticmethod
    def normalize_title(value: str) -> str:
        value = value.lower().replace("ё", "е")
        value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _score_result(cls, query: str, item: dict[str, Any]) -> float:
        normalized_query = cls.normalize_title(query)
        query_words = set(normalized_query.split())
        titles = [item.get("title", ""), item.get("title_english") or "", item.get("title_original") or ""]
        titles.extend(item.get("title_variants", []))
        best = 0.0
        for title in titles:
            normalized = cls.normalize_title(title)
            if not normalized:
                continue
            if normalized == normalized_query:
                best = max(best, 100.0)
            elif normalized_query in normalized or normalized in normalized_query:
                best = max(best, 80.0)
            else:
                words = set(normalized.split())
                if query_words:
                    best = max(best, 50.0 * len(query_words & words) / len(query_words))
        return best

    @classmethod
    def _merge_results(cls, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for item in results:
            key = (item.get("type", ""), cls.normalize_title(item.get("title", "")))
            if key not in merged:
                item["search_score"] = cls._score_result(query, item)
                merged[key] = item
                continue

            current = merged[key]
            current_titles = set(current.get("title_variants", []))
            current_titles.update(item.get("title_variants", []))
            current["title_variants"] = list(current_titles)
            if item.get("image_url") and not current.get("image_url"):
                current["image_url"] = item["image_url"]
            current["search_score"] = max(current.get("search_score", 0), cls._score_result(query, item))

        return sorted(
            merged.values(),
            key=lambda item: (item.get("search_score", 0), item.get("score") or 0),
            reverse=True,
        )

    async def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        results = await asyncio.gather(
            *(provider.search(query, media_type) for provider in self.providers),
            return_exceptions=True,
        )
        items: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                items.extend(result)
        return self._merge_results(query, items)

    async def get_media(self, provider: str, external_id: str, media_type: str) -> dict[str, Any] | None:
        for item in self.providers:
            if item.name == provider:
                return await item.get_media(external_id, media_type)
        return None

    async def close(self) -> None:
        await asyncio.gather(*(provider.close() for provider in self.providers))
