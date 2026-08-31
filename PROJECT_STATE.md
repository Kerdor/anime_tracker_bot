# PROJECT STATE — Anime Tracker Bot

> **Canonical handoff document.** This file is the primary context for continuing development in a new chat. It describes the product intent, architecture, current repository state, local environment, tests already performed, known failures, exact fixes already made, and the next development steps.
>
> **Repository:** `https://github.com/Kerdor/anime_tracker_bot`
>
> **Branch:** `main`
>
> **Current repository commit:** `56cac7b7b0d75afac0b622d5db8f8dc18cc6d6ed` — `Fix bigint identity migration for existing PostgreSQL defaults`
>
> **Important:** The repository is the source of truth for code. This file is the source of truth for product intent and development history. Before editing code, inspect the current repository and reconcile it with this document.

---

# 0. CURRENT STATE — READ FIRST

The project is a Telegram bot for tracking anime and manga. It is being evolved from an originally MAL-centric implementation into a **canonical multi-source media tracker**.

The intended architecture is:

```text
Telegram user
    ↓
bot handlers
    ↓
MediaAggregator
    ├── Jikan / MAL
    ├── Shikimori
    └── MangaLib
    ↓
unified MediaResult
    ↓
canonical Media
    ├── MediaSource (external identities)
    ├── Genre / MediaGenre
    └── UserMedia (user library)
```

Core rule:

**Providers are data sources, not separate identities.**

If the system can confidently determine that records from multiple providers describe the same real-world work, they should point to one internal `Media` row. External IDs belong in `MediaSource`.

## Current architectural status

The multi-source refactor is substantially implemented:

- canonical internal `Media.id` is used by the bot;
- provider IDs are stored in `MediaSource`;
- `Media.mal_id` has been removed;
- `Genre.mal_id` has been removed;
- `MediaAggregator` searches Jikan, Shikimori and MangaLib concurrently;
- handlers use internal `media_id` callbacks;
- MangaLib detail loading exists;
- MangaLib/Shikimori cross-ID handling was fixed;
- migrations through the new 0005 revision exist;
- PostgreSQL has now been installed locally;
- the bot has been launched successfully and aiogram polling works;
- real provider requests have been observed;
- a real PostgreSQL migration was attempted and exposed a migration bug;
- that migration bug has since been fixed in GitHub commit `56cac7b7`.

The project is **not yet considered fully end-to-end verified**. The next immediate task is to pull the fixed migration locally, run `alembic upgrade head`, verify `alembic current`, then retest search and library operations.

---

# 1. PRODUCT VISION

The bot should eventually provide a polished Russian-language tracker where users can:

- search anime;
- search manga;
- later search manhwa, manhua and novels/ranobe;
- open detailed media cards;
- add works to a personal library;
- assign a status;
- rate works from 1 to 10;
- browse/filter their library;
- view profile/statistics;
- later receive recommendations;
- later use a Telegram Web App.

Desired product feel:

- modern;
- dark;
- clean;
- polished;
- not a primitive command-only bot.

Initial language:

```text
ru
```

Future localization should be possible without redesigning the architecture.

## Statuses

```text
planning   = 🟡 Хочу
watching   = 🔵 Смотрю / Читаю
completed  = 🟢 Завершено
paused     = ⚪ На паузе
dropped    = 🔴 Брошено
```

The user explicitly considers this status set sufficient for the first version.

Do not introduce RPG-style progress, energy, achievements or complicated progression unless explicitly requested.

## Rating

```text
1–10
```

## Catalog strategy

Do **not** preload 100k+ works or maintain a giant manually curated catalog.

Providers should supply external catalog data. PostgreSQL should store normalized/cached media that the bot actually needs.

## Scale

Initial target: hundreds of users, with architecture that remains reasonable for thousands. Do not overengineer for millions.

## Recommendations

Planned, but not current priority. Later recommendations can use ratings, statuses, genres, metadata, related works and eventually collaborative filtering. Do not introduce ML prematurely.

---

# 2. EXTERNAL PROVIDERS

## 2.1 Jikan / MAL

File:

```text
providers/jikan.py
```

Internal provider name:

```text
mal
```

Jikan is the MAL API provider.

Useful for:

- large catalog coverage;
- MAL IDs;
- English/Japanese titles;
- scores;
- anime/manga metadata;
- future relations.

Search endpoints:

```text
anime → /anime
manga → /manga
```

Current search limit is 25. Local normalization/relevance ranking is applied by the aggregator.

Provider-level `mal_id` is legitimate when it represents a real MAL external identity. It must not become the internal canonical identity again.

## 2.2 Shikimori

File:

```text
providers/shikimori.py
```

Provider name:

```text
shikimori
```

Default API base:

```text
https://shikimori.one/api
```

Search:

```text
anime → /animes
manga → /mangas
```

Shikimori is especially valuable for Russian titles because the API exposes `russian`.

Parser handles fields such as:

- Shikimori ID;
- MAL ID when supplied;
- Russian title;
- English/name title;
- original title;
- variants;
- image;
- score;
- year;
- description;
- genres;
- URL;
- episode/chapter/volume counts.

During local testing, `shikimori.one` returned HTTP 301 and the configured/followed endpoint `shikimori.io` returned HTTP 200 for the Naruto query. This provider therefore produced usable data during the test.

## 2.3 MangaLib

File:

```text
providers/mangalib.py
```

Provider name:

```text
mangalib
```

Default base:

```text
https://mangalib.me
```

Search endpoint currently used:

```text
/search?type=manga&q=<query>
```

Detail endpoint:

```text
/manga-short-info
```

Parser understands fields including:

- `rus_name`;
- `name`;
- `eng_name`;
- `otherNames`;
- `id`;
- `slug`;
- `coverImage` / `cover`;
- `releaseDate`;
- `summary`;
- categories;
- chapters;
- rating;
- status.

The parser reads MangaLib `shiki_id` as:

```text
source_ids["shikimori"]
```

It must **not** be treated as a MAL ID.

This was fixed in commit:

```text
7a11adc5 — fix: map MangaLib Shikimori IDs correctly
```

During the latest local search test MangaLib returned HTTP 404 for its search URL. This is a provider-side/API compatibility issue to investigate later; it should not be allowed to crash the whole aggregator.

## 2.4 Remanga

Planned only.

It is not currently implemented or wired into `MediaAggregator`.

Do not claim Remanga support until a real provider exists.

---

# 3. SEARCH ARCHITECTURE

Intended flow:

```text
user query
    ↓
normalize query
    ↓
parallel provider searches
    ↓
collect successful results
    ↓
normalize metadata
    ↓
identity matching
    ↓
title/year deduplication
    ↓
merge metadata + source IDs
    ↓
rank
    ↓
Telegram result buttons
```

Search should understand:

- Russian titles;
- English titles;
- original/Japanese titles;
- alternate titles;
- abbreviations;
- punctuation differences;
- `ё` vs `е`;
- capitalization;
- reasonable word overlap.

Current normalization in `MediaAggregator`:

- lowercases;
- replaces `ё` with `е`;
- removes punctuation;
- collapses whitespace.

Current aggregator file:

```text
providers/aggregator.py
```

Class:

```python
MediaAggregator
```

Default providers:

```python
JikanClient()
ShikimoriClient()
MangaLibClient()
```

Provider searches use:

```python
asyncio.gather(..., return_exceptions=True)
```

Therefore one provider failure should not remove all provider results.

Aggregator responsibilities currently include:

- title normalization;
- search relevance scoring;
- provider ID collection;
- `source_ids` creation;
- exact provider identity merging;
- cross-source ID preservation;
- second title-based deduplication;
- year-aware title deduplication;
- variant merging;
- metadata merging;
- ranking by relevance/provider score.

## Entity resolution safety rule

Preferred confidence order:

1. same external provider ID;
2. explicit cross-source identity such as known MAL/Shikimori relation;
3. strong normalized title match;
4. type/year plus additional metadata;
5. conservative fuzzy matching only when confidence is high.

A duplicate result is safer than incorrectly merging two different works.

---

# 4. DATABASE MODEL

File:

```text
database/models.py
```

Current models:

```text
User
Media
MediaSource
UserMedia
Genre
MediaGenre
```

## User

Fields:

```text
id
telgram_id
username
first_name
language
created_at
updated_at
```

`telegram_id` is unique/indexed. `language` defaults to `ru`.

## Media

Fields:

```text
id
type
title
title_original
description
image_url
score
year
status
created_at
updated_at
```

Relationships:

```text
sources
library_entries
genres
```

Important: there is no `Media.mal_id` anymore.

`Media.id` is the canonical internal identity used by the bot and library.

## MediaSource

Fields:

```text
id
media_id
source
source_id
```

Unique constraint:

```text
(source, source_id)
```

Example:

```text
Media #42
├── mal        → 12345
├── shikimori  → 67890
└── mangalib   → 55555
```

## UserMedia

Fields:

```text
id
user_id
media_id
status
score
created_at
updated_at
```

Unique constraint:

```text
(user_id, media_id)
```

This is the user's library relation.

## Genre

Fields:

```text
id
name
```

Unique by name. `Genre.mal_id` was removed.

## MediaGenre

Many-to-many:

```text
media_id
 genre_id
```

with unique `(media_id, genre_id)`.

Genre migrations were designed to preserve valid `MediaGenre` relationships while consolidating duplicate genre names.

---

# 5. ALEMBIC / DATABASE MIGRATIONS — VERY IMPORTANT

Directory:

```text
alembic/versions/
```

Current chain:

```text
0001_initial
    ↓
0002_media_sources
    ↓
0003_source_independent_genres
    ↓
0004_typed_media_sources
    ↓
0005_bigint_identity
```

The previous PROJECT_STATE was stale and stopped at 0003. The repository now contains 0004 and 0005 as well.

## 0001_initial

Original schema. It created BIGINT/autoincrementing primary keys with PostgreSQL sequence-backed defaults.

## 0002_media_sources

Moves external identity away from `Media.mal_id` into `media_sources` and preserves old MAL IDs as source `mal`.

## 0003_source_independent_genres

Removes MAL-specific genre identity, makes genre names unique and preserves media/genre relationships while consolidating duplicates.

## 0004_typed_media_sources

Makes media source identity type-aware as implemented in the repository.

## 0005_bigint_identity — root cause and fix

The original 0005 migration attempted to execute SQL equivalent to:

```sql
ALTER TABLE "users" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY
```

for several tables.

This failed locally with PostgreSQL:

```text
asyncpg.exceptions.ObjectNotInPrerequisiteStateError:
column "id" of relation "users" already has a default
```

The reason is important:

**The initial migration already creates PostgreSQL sequence-backed defaults for the BIGINT primary keys. Adding IDENTITY on top of an existing default is invalid. The existing defaults are already sufficient for SQLAlchemy inserts.**

The fixed 0005 migration is intentionally a no-op:

```python
def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

The migration documentation explains that the existing PostgreSQL defaults must be preserved.

The fix was committed to GitHub as:

```text
56cac7b7b0d75afac0b622d5db8f8dc18cc6d6ed
Fix bigint identity migration for existing PostgreSQL defaults
```

GitHub file currently contains the fixed migration.

### IMPORTANT LOCAL STATE

The user ran `alembic upgrade head` against the **old/broken 0005** and got the failure above.

Because PostgreSQL DDL was transactional, the failed migration did not partially apply the 0005 schema change. The database should remain at the previous migration revision until the corrected 0005 is pulled and successfully applied.

### Exact next commands

From the project directory:

```bat
git pull
alembic upgrade head
alembic current
```

Expected final Alembic revision:

```text
0005_bigint_identity
```

Do not delete/recreate the database merely to solve this issue.

Do not manually modify PostgreSQL internals unless a new concrete error requires it.

---

# 6. DATABASE REPOSITORY

File:

```text
database/repository.py
```

Important functions include:

```python
get_or_create_user(...)
get_media(...)
get_media_by_source(...)
save_media(...)
add_to_library(...)
get_library(...)
get_library_entry(...)
update_status(...)
update_score(...)
remove_from_library(...)
get_user_statistics(...)
```

`get_media()` resolves by internal `Media.id` and eager-loads sources/genres.

`get_media_by_source()` resolves by:

```text
source + source_id
```

`save_media()` is intended to:

1. find existing media by provider/provider ID;
2. otherwise search `source_ids`;
3. create canonical Media if necessary;
4. update available metadata;
5. create missing MediaSource records;
6. create/reuse genres;
7. commit.

Potential future race condition: two users could save the same new external title concurrently. DB uniqueness is the main protection. Only add retry/upsert handling if real `IntegrityError` concurrency is observed.

---

# 7. BOT HANDLERS / CALLBACK ARCHITECTURE

File:

```text
bot/handlers.py
```

Search now uses:

```python
MediaAggregator
```

Canonical callbacks:

```text
media:<media_id>
add:<media_id>
status:<media_id>:<status>
edit_status:<media_id>
rate:<media_id>
rating:<media_id>:<score>
remove:<media_id>
library_media:<media_id>
```

Do not reintroduce callbacks using MAL IDs as canonical identities.

Current flow:

```text
/start
 ↓
main menu
 ↓
search
 ↓
anime or manga
 ↓
query
 ↓
MediaAggregator
 ↓
results
 ↓
internal media_id
 ↓
media card
 ↓
add to library / status / rating
```

---

# 8. LIBRARY / PROFILE

`bot/library.py` provides source-independent library behavior because `UserMedia` points to `Media.id`.

Current library sections:

- anime;
- manga.

Filters:

- all;
- completed;
- watching;
- planning;
- paused;
- dropped.

Supported actions:

- open media;
- change status;
- rate 1–10;
- remove;
- return to library;
- pagination.

`bot/profile.py` provides basic profile/statistics functionality, including library size, type/status counts and average score.

Do not overbuild statistics before the core search/library flow is stable.

---

# 9. MEDIA DETAILS

Media cards can display, when available:

- title;
- original title;
- year;
- provider score;
- anime episode count;
- manga chapter/volume counts;
- genres;
- description;
- image.

`MediaAggregator.get_media()` attempts to use available provider details and merges metadata when one provider lacks a field.

Provider errors should not unnecessarily destroy the card.

Current limitation: details are fetched on demand. There is no mature freshness/cache policy yet. Add caching later after end-to-end correctness is verified.

---

# 10. LOCAL ENVIRONMENT — VERIFIED

OS:

```text
Windows 10 22H2
```

Architecture:

```text
AMD64
```

Python:

```text
Python 3.12
```

Project directory:

```text
C:\Users\nik_s\OneDrive\Рабочий стол\ALL\it\projects\python\tg\anime_tracker_bot
```

PostgreSQL has been installed locally and is being used directly. Docker is **not** required for current local development.

The user has limited disk space (about 46 GB free was reported). Do not introduce Docker/WSL/container requirements unless they are genuinely needed.

During setup, WSL/Virtual Machine Platform components were installed while investigating Docker compatibility. The project itself does not depend on Linux or Docker for the current local workflow.

`.env` exists locally and contains the bot/database configuration. Never ask the user to paste real secrets into chat.

---

# 11. DEPENDENCY / HTTP2 ISSUE THAT WAS ALREADY FIXED LOCALLY

Initial provider search crashed with:

```text
ImportError: Using http2=True, but the 'h2' package is not installed.
Make sure to install httpx using `pip install httpx[http2]`.
```

The traceback originated from:

```text
providers/mangalib.py
```

where `httpx.AsyncClient(..., http2=True)` is created.

The issue was resolved locally by installing the HTTP/2 dependency. Subsequent logs show MangaLib requests using:

```text
HTTP/2
```

Therefore do not re-diagnose this as the current problem unless the environment is rebuilt and the dependency disappears.

The requirements file should eventually explicitly guarantee the required HTTP/2 dependency so another machine does not reproduce this failure.

---

# 12. REAL BOT TESTS ALREADY PERFORMED

The bot was launched successfully with:

```bat
C:\Users\nik_s\AppData\Local\Programs\Python\Python312\python.exe main.py
```

Aiogram reported:

```text
Start polling
Run polling for bot @anime_tracker_hub_bot id=8868382935 - 'Anime Tracker'
```

So Telegram polling and the bot token/configuration are working.

Basic `/start` interaction worked and the bot sent:

```text
🔎 Введи название аниме:
```

## Search test: Naruto

Queries tested:

```text
наруто
Наруто
Naruto
```

Observed provider requests included:

```text
Jikan:
GET https://api.jikan.moe/v4/anime?q=...&limit=25&sfw=true
→ HTTP 504 Gateway Time-out
```

```text
Shikimori:
GET https://shikimori.one/api/animes?search=...&limit=20
→ HTTP 301 Moved Permanently
```

followed by:

```text
GET https://shikimori.io/api/animes?search=...&limit=20
→ HTTP 200 OK
```

and:

```text
MangaLib:
GET https://mangalib.me/search?type=manga&q=...
→ HTTP 404 Not Found
```

The bot handled the update rather than crashing, but the user saw either:

```text
Ничего не найдено. Попробуй другое название.
```

or:

```text
Не удалось сохранить результаты поиска. Попробуй ещё раз позже.
```

This happened before the fixed 0005 migration was pulled/applied, so the search/save path must be retested after the DB reaches the corrected head.

### Important interpretation

There are at least two independent external-provider issues visible in the test:

1. Jikan returned 504.
2. MangaLib search returned 404.

Shikimori returned 200 after redirect handling.

The aggregator is already designed to tolerate provider exceptions. Therefore, after the DB migration is fixed, the next question is whether the Shikimori result is correctly persisted and displayed even when Jikan/MangaLib fail.

Do not assume the provider errors are the same bug as the database save error.

---

# 13. PREVIOUS MIGRATION TEST HISTORY

Earlier, before 0005 was introduced, the local database successfully ran:

```text
0001_initial
0002_media_sources
0003_source_independent_genres
0004_typed_media_sources
```

The user then pulled a new migration and ran:

```bat
alembic upgrade head
```

The old 0005 failed exactly at:

```sql
ALTER TABLE "users" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY
```

with:

```text
column "id" of relation "users" already has a default
```

The fix is now already committed to GitHub. The local clone needs to pull it.

---

# 14. CURRENT GITHUB STATE

Current `main` HEAD:

```text
56cac7b7b0d75afac0b622d5db8f8dc18cc6d6ed
```

Commit message:

```text
Fix bigint identity migration for existing PostgreSQL defaults
```

The commit changes only:

```text
alembic/versions/0005_bigint_identity.py
```

Old behavior:

```python
from alembic import op

_TABLES = ("users", "media", "genres", "user_media", "media_sources")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY'
        )
```

New behavior:

```python
def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

Reason: PostgreSQL's existing sequence-backed defaults are already sufficient and must not be converted to IDENTITY.

The user must run `git pull` before retrying the migration.

---

# 15. CURRENT PROJECT STRUCTURE

Expected current structure:

```text
anime_tracker_bot/
│
├── .env.example
├── .gitignore
├── PROJECT_STATE.md
├── README.md
├── alembic.ini
├── config.py
├── docker-compose.yml
├── main.py
├── requirements.txt
│
├── alembic/
│   ├── __init__.py
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial.py
│       ├── 0002_media_sources.py
│       ├── 0003_source_independent_genres.py
│       ├── 0004_typed_media_sources.py
│       └── 0005_bigint_identity.py
│
├── api/
├── bot/
│   ├── __init__.py
│   ├── handlers.py
│   ├── keyboards.py
│   ├── library.py
│   └── profile.py
│
├── database/
│   ├── __init__.py
│   ├── base.py
│   ├── models.py
│   ├── repository.py
│   └── session.py
│
└── providers/
    ├── __init__.py
    ├── aggregator.py
    ├── base.py
    ├── jikan.py
    ├── mangalib.py
    └── shikimori.py
```

Do not split this into many services/layers without a concrete need.

---

# 16. README STATUS

`README.md` exists but remains relatively minimal compared with the current architecture.

Eventually it should document:

- multi-source architecture;
- Jikan/MAL;
- Shikimori;
- MangaLib;
- canonical `Media` + `MediaSource` model;
- PostgreSQL setup;
- Alembic migrations;
- bot features;
- local development workflow.

Do not spend time rewriting README until the current runtime and DB flow are stable.

---

# 17. KNOWN PROBLEMS / TECHNICAL DEBT — PRIORITIZED

## CRITICAL — local database must reach migration 0005

Current known local failure is the old 0005 IDENTITY migration. GitHub now contains the fixed no-op migration.

Next action:

```bat
git pull
alembic upgrade head
alembic current
```

## HIGH — search/save must be retested after DB fix

The bot can poll Telegram and provider requests work, but search results were not successfully persisted/displayed during the first real DB test.

Retest with:

```text
Naruto
```

Prefer a Russian query too:

```text
наруто
```

Observe whether Shikimori results are saved and shown when Jikan/MangaLib fail.

## HIGH — Jikan 504

Jikan returned HTTP 504 during the Naruto test. This may be temporary or provider-side. The aggregator must remain functional when Jikan is unavailable.

Do not make Jikan a single point of failure.

## HIGH — MangaLib search 404

MangaLib search endpoint currently returned 404. Investigate the current MangaLib API/search mechanism later. Do not let it break Shikimori/Jikan results.

## HIGH — provider entity resolution remains heuristic

Keep identity matching conservative. Prefer false duplicates over false merges.

## HIGH — `save_media()` concurrency race is possible

Only fix with focused upsert/retry handling if real concurrent `IntegrityError` is observed.

## MEDIUM — detail caching

Provider details are loaded on demand. Add a sensible cache/refresh policy later.

## MEDIUM — only anime/manga in current UI

Future media types should fit the flexible architecture rather than getting separate tables without need.

## MEDIUM — Remanga not implemented

Add only after current three-provider flow is stable.

---

# 18. EXACT NEXT DEVELOPMENT ORDER

## STEP 1 — Pull fixed migration

Run:

```bat
git pull
```

Expected GitHub commit:

```text
56cac7b7b0d75afac0b622d5db8f8dc18cc6d6ed
```

## STEP 2 — Run migration

```bat
alembic upgrade head
```

Expected successful output should include:

```text
Running upgrade 0004_typed_media_sources -> 0005_bigint_identity
```

with no traceback.

Then:

```bat
alembic current
```

Expected:

```text
0005_bigint_identity
```

## STEP 3 — Launch bot

```bat
python main.py
```

or the user's explicit Python 3.12 executable if needed.

## STEP 4 — Search test

Test:

```text
/start
→ Аниме
→ наруто
```

Then:

```text
Naruto
```

Check that provider failures do not prevent successful Shikimori results from appearing.

## STEP 5 — Open a result

Verify:

- result button works;
- internal `media_id` is used;
- media card loads;
- image/description/title metadata are shown;
- no callback references MAL as canonical identity.

## STEP 6 — Add to library

Verify:

```text
add
→ choose status
→ library
```

## STEP 7 — Change status/rating/remove

Test every status and at least one rating.

## STEP 8 — Manga

Repeat search/card/library flow for a manga.

## STEP 9 — Cross-source identity

Find a title available in multiple providers and verify:

- one canonical `Media` row;
- multiple `MediaSource` rows;
- one `UserMedia` row;
- provider IDs preserved.

## STEP 10 — Fix concrete provider/search issues

After DB correctness is proven:

- investigate MangaLib 404;
- improve Jikan resilience/retry only if justified;
- inspect search ranking/duplicates;
- improve Russian/alternate title matching.

## STEP 11 — Only then continue feature development

Possible order:

1. richer media cards;
2. detail caching;
3. Remanga provider;
4. better statistics;
5. API layer;
6. Telegram Web App;
7. recommendations.

---

# 19. DO NOT DO YET

Do not currently:

- preload huge catalogs;
- build ML recommendations;
- build RPG/gamification systems;
- add complicated progress mechanics;
- build microservices;
- aggressively fuzzy-merge titles;
- restore MAL as canonical identity;
- require Docker for local development;
- rebuild the database blindly;
- manually edit PostgreSQL internals without a concrete error;
- build the Web App before the backend is stable.

---

# 20. CODING / EDITING RULES — USER REQUIREMENTS

The user wants the assistant to behave as a technical editor.

1. Find the concrete problem first.
2. Explain it briefly and directly.
3. Preserve existing logic and architecture unless a change is necessary.
4. Make the smallest reasonable fix.
5. Do not add unnecessary libraries.
6. Preserve formatting and 4-space Python indentation.
7. Never use `...` as a placeholder for omitted code.
8. If changing a function, provide the complete function.
9. Prefer `БЫЛО → СТАЛО` for local replacements.
10. Do not ask the user to replace a huge file when only a small function changes.
11. If several issues exist, list them by priority:

```text
КРИТИЧНО
ВЫСОКИЙ ПРИОРИТЕТ
СРЕДНИЙ
```

12. If the user says `давай`, `делай` or `продолжай`, take the next logical development step without unnecessary confirmation.
13. Do not claim something works unless it has actually been tested.
14. When repository tools are available, inspect the current GitHub code before editing it.

---

# 21. GIT WORKFLOW

Repository:

```text
Kerdor/anime_tracker_bot
```

Branch:

```text
main
```

Normal local commands:

```bat
git status
git pull
git log --oneline -10
alembic current
alembic upgrade head
python main.py
```

When changing code:

1. inspect current file;
2. preserve newer changes;
3. make focused change;
4. commit with a meaningful message;
5. verify GitHub write;
6. tell the user the commit SHA/message;
7. user can run `git pull` locally.

Never tell the user to blindly discard local changes.

---

# 22. IMPORTANT PROJECT SEPARATION

This state file belongs ONLY to:

```text
Kerdor/anime_tracker_bot
```

Do not confuse it with:

```text
InsaneBot-discord
nightmare_spire_bot
solo_rank_bot
```

Those projects have unrelated architectures and state.

---

# 23. NEW CHAT HANDOFF INSTRUCTIONS

When continuing in a new chat:

1. Read this `PROJECT_STATE.md` first.
2. Check the current GitHub `main` commit because this file can become stale after future commits.
3. Do not ask the user to repeat the history documented here.
4. Do not assume a file is correct merely because it exists; inspect integration points.
5. Preserve the product decisions unless the user explicitly changes them.
6. Treat provider failures independently from database failures.
7. Never assume Docker is required.
8. Never ask for real secrets.
9. Follow the user's coding/editing rules exactly.
10. If the user says `давай/делай/продолжай`, continue with the next logical task.
11. Keep explanations practical and in Russian.
12. Do not claim end-to-end success until the actual migration and Telegram search/library flow have been tested.

### Immediate continuation point

The project is currently paused at this exact point:

```text
GitHub:
56cac7b7 Fix bigint identity migration for existing PostgreSQL defaults

Local:
old 0005 migration was executed and failed because PostgreSQL id columns already
have sequence-backed defaults.

Next:
git pull
alembic upgrade head
alembic current
then run the bot and retest Naruto search.
```

After that, investigate whether the search result persistence error is gone. If it remains, inspect `database/repository.py`, `bot/handlers.py`, the current migration/schema state, and the exact traceback before changing anything.

---

# 24. ONE-LINE SUMMARY

> **Anime Tracker Bot has successfully moved toward a canonical multi-source architecture (`Media → MediaSource → UserMedia`), the bot itself polls Telegram and provider requests are functioning, PostgreSQL is installed locally, migrations 0001–0004 were previously applied, the newly introduced 0005 migration was proven incorrect against real PostgreSQL and has now been fixed on GitHub as a no-op because the initial schema already provides sequence-backed BIGINT defaults; the exact next step is to pull commit `56cac7b7`, run `alembic upgrade head`, verify revision 0005, then retest Naruto search and the full add/status/rating/library flow.**
