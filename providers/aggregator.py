import asyncio
import re
from typing import Any

from providers.base import MediaProvider
from providers.jikan import JikanClient
from providers.mangalib import MangaLibClient
from providers.shikimori import ShikimoriClient


class MediaAggregator:
    def __init__(self, providers: list[MediaProvider] | None = None) -> None:
        self.providers = providers or [JikanClient(), ShikimoriClient(), MangaLibClient()]

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
    def _identity_keys(cls, item: dict[str, Any]) -> set[tuple[str, str]]:
        keys: set[tuple[str, str]] = set()
        provider = item.get("provider")
        provider_id = item.get("provider_id")
        if provider and provider_id:
            keys.add((provider, str(provider_id)))
        mal_id = item.get("mal_id")
        if mal_id:
            keys.add(("mal", str(mal_id)))
        for source, source_id in item.get("source_ids", {}).items():
            if source and source_id:
                keys.add((source, str(source_id)))
        return keys

    @classmethod
    def _merge_results(cls, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        identity_map: dict[tuple[str, str], int] = {}

        for item in results:
            item = dict(item)
            item["search_score"] = cls._score_result(query, item)
            item["providers"] = [item.get("provider")] if item.get("provider") else []
            item["source_ids"] = dict(item.get("source_ids", {}))
            if item.get("provider") and item.get("provider_id"):
                item["source_ids"][item["provider"]] = str(item["provider_id"])
            if item.get("mal_id"):
                item["source_ids"]["mal"] = str(item["mal_id"])

            matched_index = None
            for key in cls._identity_keys(item):
                if key in identity_map:
                    matched_index = identity_map[key]
                    break

            if matched_index is None:
                matched_index = len(merged)
                merged.append(item)
            else:
                current = merged[matched_index]
                current_titles = set(current.get("title_variants", []))
                current_titles.update(item.get("title_variants", []))
                for field in ("title", "title_english", "title_original"):
                    if item.get(field):
                        current_titles.add(item[field])
                current["title_variants"] = list(current_titles)

                for field in ("image_url", "description", "title_english", "title_original", "url", "score", "year"):
                    if item.get(field) and not current.get(field):
                        current[field] = item[field]

                if item.get("mal_id") and not current.get("mal_id"):
                    current["mal_id"] = item["mal_id"]

                current["providers"] = sorted(set(current.get("providers", [])) | set(item.get("providers", [])))
                current["source_ids"].update(item.get("source_ids", {}))
                current["search_score"] = max(current.get("search_score", 0), item["search_score"])

            for key in cls._identity_keys(item):
                identity_map[key] = matched_index

        title_map: dict[tuple[str, str, int | None], int] = {}
        final: list[dict[str, Any]] = []
        for item in merged:
            key = (
                item.get("type", ""),
                cls.normalize_title(item.get("title", "")),
                item.get("year"),
            )
            if key not in title_map:
                title_map[key] = len(final)
                final.append(item)
                continue

            current = final[title_map[key]]
            current["title_variants"] = list(set(current.get("title_variants", [])) | set(item.get("title_variants", [])))
            current["providers"] = sorted(set(current.get("providers", [])) | set(item.get("providers", [])))
            current["source_ids"].update(item.get("source_ids", {}))
            current["search_score"] = max(current.get("search_score", 0), item.get("search_score", 0))

        return sorted(
            final,
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

    async def get_media(self, media, media_type: str) -> dict[str, Any] | None:
        providers = {provider.name: provider for provider in self.providers}
        sources = sorted(
            media.sources,
            key=lambda source: (0 if source.source == "shikimori" else 1 if source.source == "mal" else 2),
        )

        details: dict[str, Any] | None = None
        for source in sources:
            provider = providers.get(source.source)
            if provider is None:
                continue
            try:
                item = await provider.get_media(source.source_id, media_type)
            except Exception:
                continue
            if item is None:
                continue

            if details is None:
                details = item
            else:
                for field in ("title", "title_english", "title_original", "description", "image_url", "score", "year", "episodes", "chapters", "volumes", "url"):
                    if details.get(field) is None and item.get(field) is not None:
                        details[field] = item[field]
                details["genres"] = list(dict.fromkeys((details.get("genres") or []) + (item.get("genres") or [])))
                details["title_variants"] = list(dict.fromkeys((details.get("title_variants") or []) + (item.get("title_variants") or [])))

        return details

    async def close(self) -> None:
        await asyncio.gather(*(provider.close() for provider in self.providers))
