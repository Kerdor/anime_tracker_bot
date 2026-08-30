# PROJECT STATE — Anime Tracker Bot

> **Canonical handoff document.** This file describes the current product decisions, architecture, repository state, completed work, known problems and the exact next steps for continuing development in a new chat.
>
> **Repository:** `https://github.com/Kerdor/anime_tracker_bot`
>
> **Branch:** `main`
>
> **Last verified repository commit:** `7a11adc5e7078f55955c2a83500c3b56cef98394` (`fix: map MangaLib Shikimori IDs correctly`)
>
> **Important:** The actual repository is authoritative for code. This file is authoritative for product intent and project history. Before making changes, inspect the current repository and reconcile it with this document.

---

# 0. CURRENT STATE — READ THIS FIRST

The project is a Telegram tracker for anime and manga, being evolved into a **multi-source media tracker**.

The core architectural transition is now substantially implemented:

```text
Telegram user
     │
     ▼
Bot handlers
     │
     ▼
MediaAggregator
     │
     ├── Jikan / MAL
     ├── Shikimori
     └── MangaLib
     │
     ▼
Unified search result
     │
     ▼
Canonical Media
     │
     ├── MediaSource (one or more external IDs)
     ├── Genre / MediaGenre
     └── UserMedia
```

The important design decision is:

**External providers are data sources, not separate libraries.**

A real-world work should be represented by one internal `Media` row whenever the system can confidently determine that multiple provider records refer to the same work. External IDs are stored in `MediaSource`.

## Current verified migration state

Alembic migrations now exist as:

```text
0001_initial
    ↓
0002_media_sources
    ↓
0003_source_independent_genres
```

Current Alembic head in the repository is therefore:

```text
0003_source_independent_genres
```

The old state document was stale and incorrectly claimed that only `0001_initial` existed. This document supersedes that information.

## Current verified model state

`database/models.py` contains:

```text
User
Media
MediaSource
UserMedia
Genre
MediaGenre
```

`Media` no longer contains `mal_id`.

`Genre` no longer contains `mal_id`.

`MediaSource` stores external identities as:

```text
source
source_id
```

with a unique constraint on:

```text
(source, source_id)
```

## Current verified bot flow

`bot/handlers.py` now uses `MediaAggregator` for search and internal `media_id` callback values.

The current callback design is source-independent:

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

This replaces the previous MAL-dependent callback concept.

## Current providers

Implemented provider classes:

```text
JikanClient
ShikimoriClient
MangaLibClient
```

Remanga is still planned and is not implemented yet.

## Current known important limitation

The project has **not yet been run end-to-end against a real local PostgreSQL database in this development session**. The repository contains migrations, but database migration execution and real Telegram/API testing still need to be verified locally.

Do not tell the user that the whole bot is proven working until that test has been performed.

---

# 1. PRODUCT VISION

The bot should become a polished Telegram tracker where a user can:

- search anime;
- search manga;
- later search manhwa;
- later search manhua;
- later search novels/ranobe;
- add works to a personal library;
- assign a status;
- rate works from 1 to 10;
- browse the library;
- view profile/statistics;
- later receive recommendations;
- later use a Telegram Web App with a richer interface.

The user wants a product that feels **modern, dark, clean and polished**, not a primitive command-only bot.

Initial language:

```text
Russian (ru)
```

The architecture should make future localization possible without redesigning the whole application.

---

# 2. PRODUCT DECISIONS

## 2.1 Statuses

The current status set is intentionally simple:

```text
planning   = 🟡 Хочу
watching   = 🔵 Смотрю / Читаю
completed  = 🟢 Завершено
paused     = ⚪ На паузе
dropped    = 🔴 Брошено
```

The user explicitly said that status is enough for the first version.

Do **not** introduce an RPG-like progress/energy/achievement system or complicated progress mechanics unless explicitly requested.

## 2.2 Rating

User rating:

```text
1–10
```

## 2.3 Catalog strategy

The user does not want to manually maintain a giant catalog containing 100k+ anime and an even larger manga/manhwa/etc. catalog.

Therefore:

- providers supply external catalog data;
- PostgreSQL stores normalized/cached media that the bot actually needs;
- do not preload entire external catalogs;
- do not turn the bot into a huge static database project.

## 2.4 Scale

Initial expected scale:

```text
hundreds of users
```

Architecture should remain reasonable for thousands of users, but there is no need to overengineer for millions yet.

## 2.5 Recommendations

Recommendations are planned but are **not current priority**.

Later they can use:

- ratings;
- statuses;
- genres;
- authors/studios;
- related works;
- content similarity;
- eventually collaborative filtering.

Do not introduce ML prematurely.

---

# 3. EXTERNAL SOURCES

## 3.1 Jikan / MAL

File:

```text
providers/jikan.py
```

Provider name:

```text
mal
```

Jikan is the MAL API provider.

It is useful for:

- large catalog coverage;
- MAL IDs;
- English/Japanese titles;
- scores;
- anime/manga metadata;
- future relations and other metadata.

Search endpoints currently follow the standard type split:

```text
anime → /anime
manga → /manga
```

The current search implementation uses a limit of 25 and has local title normalization/relevance ranking.

Jikan should not be treated as the only Russian-language search source.

## 3.2 Shikimori

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

Search endpoints:

```text
anime → /animes
manga → /mangas
```

Shikimori is especially valuable for Russian titles because its API exposes `russian`.

The parser handles data including:

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

## 3.3 MangaLib

File:

```text
providers/mangalib.py
```

Provider name:

```text
mangalib
```

Default base URL:

```text
https://mangalib.me
```

Current search endpoint:

```text
/search
```

with parameters equivalent to:

```text
type=manga
q=<query>
```

The current parser knows about fields such as:

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

`get_media()` is now implemented using the MangaLib short-info endpoint.

Current detail endpoint:

```text
/manga-short-info
```

The parser also reads `shiki_id` and stores it as:

```text
source_ids["shikimori"]
```

It must **not** be treated as a MAL ID.

This was explicitly fixed in commit:

```text
7a11adc5
fix: map MangaLib Shikimori IDs correctly
```

## 3.4 Remanga

Remanga is planned.

It is **not currently implemented** in the provider list.

Do not claim it is supported until an actual provider has been added and wired into `MediaAggregator`.

---

# 4. SEARCH ARCHITECTURE

The intended search flow is:

```text
User query
   ↓
normalize query
   ↓
parallel provider searches
   ↓
collect provider results
   ↓
normalize metadata
   ↓
identity matching
   ↓
title/year deduplication
   ↓
merge metadata
   ↓
rank
   ↓
Telegram result buttons
```

## Required search behavior

The bot should eventually handle equivalent queries such as:

```text
Розовая пора моей школьной жизни сплошной обман
Как и ожидалось, моя школьная жизнь...
Oregairu
Yahari Ore no Seishun Love Comedy wa Machigatteiru
```

Search should understand:

- Russian titles;
- English titles;
- original/Japanese titles;
- alternate titles;
- abbreviated titles;
- punctuation differences;
- `ё` versus `е`;
- capitalization differences;
- reasonable word overlap.

Current normalization in `MediaAggregator`:

- lowercases;
- replaces `ё` with `е`;
- removes punctuation;
- collapses whitespace.

## Current aggregator implementation

File:

```text
providers/aggregator.py
```

Class:

```python
MediaAggregator
```

Current default providers:

```python
JikanClient()
ShikimoriClient()
MangaLibClient()
```

Searches run concurrently with:

```python
asyncio.gather(..., return_exceptions=True)
```

Therefore a provider failure should not remove all results.

The aggregator currently:

- normalizes titles;
- scores search relevance;
- collects provider IDs;
- creates `source_ids` mappings;
- merges exact provider identities;
- preserves cross-source IDs;
- performs a second title-based deduplication pass;
- makes title deduplication year-aware;
- merges variants and metadata;
- ranks by search relevance and provider score.

## Important limitation

Entity resolution is still heuristic.

Never aggressively fuzzy-merge two works only because their names look similar.

Preferred confidence order:

1. same external provider ID;
2. explicit cross-source identity such as a known MAL/Shikimori relation;
3. strong normalized title match;
4. type/year and additional metadata;
5. conservative fuzzy matching only when confidence is high.

A duplicate is safer than incorrectly merging two different works.

---

# 5. DATABASE MODEL — CURRENT

File:

```text
database/models.py
```

## 5.1 User

Fields:

```text
id
telegram_id
username
first_name
language
created_at
updated_at
```

`telegram_id` is unique and indexed.

`language` defaults to `ru`.

## 5.2 Media

Current fields:

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

**Important:** `Media` no longer has `mal_id`.

The internal `Media.id` is the canonical identity used by the bot/library.

## 5.3 MediaSource

Current fields:

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

All can point to one canonical `Media` when identity matching is reliable.

## 5.4 UserMedia

Current fields:

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

## 5.5 Genre

Current fields:

```text
id
name
```

Unique constraint:

```text
name
```

Genre is now source-independent.

The previous MAL-specific `mal_id` was removed.

## 5.6 MediaGenre

Many-to-many relation:

```text
media_id
 genre_id
```

with unique `(media_id, genre_id)`.

The migration was specifically written to preserve existing `media_genres` links when duplicate genre names are consolidated.

---

# 6. ALEMBIC / MIGRATIONS — CURRENT

Directory:

```text
alembic/versions/
```

Current migrations:

```text
0001_initial.py
0002_media_sources.py
0003_source_independent_genres.py
```

## 6.1 0001_initial

Creates the original schema.

At that point `Media` and `Genre` were MAL-centric:

```text
Media.mal_id
Genre.mal_id
```

## 6.2 0002_media_sources

Revision:

```text
0002_media_sources
```

Revises:

```text
0001_initial
```

Purpose:

- creates `media_sources`;
- copies existing `media.mal_id` values into `media_sources` as source `mal`;
- removes `media.mal_id`;
- adds the `(source, source_id)` uniqueness rule.

This is the main migration from MAL identity to provider identity.

## 6.3 0003_source_independent_genres

Revision:

```text
0003_source_independent_genres
```

Revises:

```text
0002_media_sources
```

Purpose:

- removes `Genre.mal_id`;
- makes genre name unique;
- consolidates duplicate genre rows by name;
- preserves `MediaGenre` links while consolidating duplicates.

## Migration warning

The migrations have been authored but have **not yet been confirmed against a real PostgreSQL instance during the current development session**.

Before declaring the DB layer production-ready, run:

```bat
alembic upgrade head
alembic current
```

against a valid local PostgreSQL database.

Do not manually drop/recreate the database just to make the migration pass.

Do not ask the user to expose their real `BOT_TOKEN` or database password in chat.

---

# 7. DATABASE REPOSITORY — CURRENT

File:

```text
database/repository.py
```

The repository is now source-independent at the core level.

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

## `get_media`

Looks up by internal:

```text
Media.id
```

and eager-loads:

```text
Media.sources
Media.genres
```

## `get_media_by_source`

Looks up by:

```text
source
source_id
```

This is the correct way to resolve a provider identity.

## `save_media`

Current intended behavior:

1. look for an existing media by `provider/provider_id`;
2. if not found, look through `source_ids`;
3. create canonical `Media` if necessary;
4. update available metadata;
5. create missing `MediaSource` records;
6. create/reuse genres by name;
7. commit.

This is the main persistence bridge from aggregator results into the canonical database model.

## Important remaining repository concern

`save_media()` is currently good enough for the current flow but should be reviewed for race conditions if multiple users select the same new external title concurrently. The DB unique constraint protects `(source, source_id)`, but application-level handling of an `IntegrityError`/retry may eventually be needed.

Do not add complicated locking until a real concurrency problem is observed.

---

# 8. BOT HANDLERS — CURRENT

File:

```text
bot/handlers.py
```

The current handler flow uses:

```python
from providers.aggregator import MediaAggregator
```

Search flow:

```text
search button
    ↓
select anime/manga
    ↓
enter query
    ↓
MediaAggregator.search()
    ↓
save results through repository
    ↓
assign internal media_id
    ↓
show result buttons
```

Result callbacks now use canonical internal IDs.

## Current media detail flow

When a user opens a media result or library entry:

```text
internal media_id
    ↓
get_media()
    ↓
Media + MediaSource(s)
    ↓
MediaAggregator.get_media()
    ↓
provider details
    ↓
merge with canonical data
    ↓
Telegram media card
```

The aggregator's detail loader tries available providers based on the stored source records.

Current provider preference in `get_media()` is approximately:

```text
Shikimori
MAL/Jikan
MangaLib
```

with additional metadata merged when the first provider does not contain a field.

Provider errors are caught so one unavailable provider does not necessarily destroy the card.

## Current media card

The card can display:

- title;
- original title;
- year;
- external score;
- episode count for anime;
- chapter/volume counts for manga;
- genres;
- description;
- image when available.

## Important limitation

The current detail merge is not yet a full metadata synchronization system.

It loads details on demand but does not yet implement a robust cache/refresh policy.

That should be addressed later, after end-to-end behavior is verified.

---

# 9. BOT KEYBOARDS — CURRENT

File:

```text
bot/keyboards.py
```

Main menu currently contains:

```text
🎬 Аниме
📚 Манга
🔎 Поиск
👤 Мой профиль
📊 Статистика
```

Search type:

```text
🎬 Аниме
📚 Манга
```

Media result buttons use:

```text
media:<media_id>
```

Library actions use internal `media_id`.

Rating uses:

```text
rating:<media_id>:<score>
```

The status set remains:

```text
planning
watching
completed
paused
dropped
```

## Important architectural rule

Do not reintroduce callbacks containing:

```text
mal_id
```

The canonical callback identity is now the internal `Media.id`.

---

# 10. LIBRARY — CURRENT

File:

```text
bot/library.py
```

Library is source-independent because `UserMedia` references:

```text
Media.id
```

not a provider ID.

Current library sections:

- anime;
- manga.

Current filters:

- all;
- completed;
- watching;
- planning;
- paused;
- dropped.

Pagination is present.

Library entries support:

- changing status;
- rating 1–10;
- removing from library;
- returning to the library.

The library should not care whether a title originated from MAL, Shikimori, MangaLib or a future provider.

---

# 11. PROFILE / STATISTICS

File:

```text
bot/profile.py
```

A basic profile/statistics foundation exists.

The repository has statistics aggregation for:

- total library size;
- media type/status counts;
- average user score.

This is intentionally basic.

Do not overbuild statistics until search/library/media identity is stable.

Future possibilities:

- completed count;
- genre distribution;
- rating distribution;
- activity over time;
- favorite genres;
- watched/read totals when reliable metadata exists.

---

# 12. PROJECT STRUCTURE — VERIFIED CURRENT REPOSITORY

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
│       └── 0003_source_independent_genres.py
│
├── api/
│   └── __init__.py
│
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

The structure is intentionally small.

Do not split it into dozens of services/layers without a concrete need.

---

# 13. APPLICATION ENTRYPOINT

File:

```text
main.py
```

Current stack:

- Python;
- aiogram;
- SQLAlchemy async;
- Alembic;
- PostgreSQL;
- httpx providers.

The dispatcher currently includes:

```text
bot.handlers.router
bot.profile.router
```

and starts aiogram polling.

---

# 14. CONFIG / LOCAL ENVIRONMENT

File:

```text
config.py
```

Required environment configuration includes:

```text
BOT_TOKEN
DATABASE_URL
```

The user must keep real secrets local.

Do not ask them to paste:

- bot token;
- database password;
- other secrets.

The repository contains `.env.example`.

## User's known local environment

Windows machine.

Example project directory:

```text
C:\Users\nik_s\OneDrive\Рабочий стол\ALL\it\projects\python\tg\anime_tracker_bot
```

Known Python version from the previous project state:

```text
Python 3.12.10
```

Known pip version:

```text
pip 26.1.2
```

Docker is not installed.

Therefore do not assume Docker is available just because `docker-compose.yml` exists.

The user is comfortable with simple CMD/Git commands but is not a database administrator.

When database setup is needed, give exact commands and short explanations.

---

# 15. README STATUS

`README.md` exists but is still relatively minimal and should eventually be updated to reflect the current architecture.

It should eventually document:

- multi-source architecture;
- Jikan/MAL;
- Shikimori;
- MangaLib;
- canonical `Media` + `MediaSource` model;
- migrations;
- setup;
- current bot features;
- local development workflow.

Do not repeatedly rewrite README for every small code change. Update it after the current architecture and local setup have stabilized.

---

# 16. COMPLETED WORK — RECENT HISTORY

The following work was completed during the current architectural transition.

## Canonical source model

Implemented:

```text
MediaSource
```

and moved external identity away from:

```text
Media.mal_id
```

toward:

```text
MediaSource(source, source_id)
```

## Genre decoupling

Removed MAL identity from `Genre`.

Genres are now keyed by their normalized stored name rather than MAL ID.

## Genre migration safety

The migration was corrected so consolidating duplicate genre names does not accidentally destroy valid `MediaGenre` relationships.

## MangaLib detail loading

Implemented MangaLib detail fetching.

## MangaLib URL handling

Corrected MangaLib media URL fallback.

## Cross-source ID preservation

Aggregator merge now preserves `source_ids` when provider results are merged.

## Year-aware title deduplication

Title deduplication now includes the work year in its secondary key to reduce accidental merging of same-title works from different years.

## MangaLib/Shikimori ID correction

A MangaLib `shiki_id` is now mapped to:

```text
source_ids["shikimori"]
```

instead of being incorrectly treated as a MAL ID.

## Media details

Media cards now attempt to load provider details through `MediaAggregator.get_media()`.

## Handler canonical IDs

Handlers and keyboards now use internal `Media.id` for callbacks and library operations.

---

# 17. RECENT COMMITS

Recent verified commits in `main` include:

```text
7a11adc5  fix: map MangaLib Shikimori IDs correctly
6d144ccc  fix: make title deduplication year aware
4bb20883  fix: preserve cross-source IDs during result merge
3ba7e92a  fix: correct MangaLib media URL fallback
03ebe7f2  feat: load MangaLib media details
066c2179  fix: preserve media genre links during migration
db0ded2a  feat: remove MAL dependency from genres
86457e22  fix: make genre storage source independent
4e090921  refactor: remove MAL identity from genres
53b25e51  feat: load provider details for media cards
```

The latest verified commit is:

```text
7a11adc5e7078f55955c2a83500c3b56cef98394
```

---

# 18. CURRENT KNOWN PROBLEMS / TECHNICAL DEBT

## CRITICAL — real DB migration has not been verified locally

The migration chain now exists, but it must be tested against PostgreSQL.

Required verification:

```bat
alembic upgrade head
alembic current
```

Expected head:

```text
0003_source_independent_genres
```

If migration fails, inspect the exact database error before changing migration logic.

Do not blindly delete the database.

## HIGH — provider details are not fully standardized

Different providers expose different metadata.

The current aggregator merges common fields such as:

```text
title
title_english
title_original
description
image_url
score
year
episodes
chapters
volumes
url
genres
title_variants
```

A more formal normalized provider DTO/schema may eventually be useful, but do not add unnecessary abstractions until actual provider differences justify them.

## HIGH — cross-provider entity resolution is heuristic

Current matching is useful but not a perfect identity system.

Potential future improvement:

```text
provider cross-links
      ↓
strong identity
      ↓
title + type + year
      ↓
conservative fuzzy matching
```

Avoid aggressive fuzzy matching.

## HIGH — concurrency race in `save_media()` is possible

Two users can theoretically save the same provider record at the same time.

The DB uniqueness constraint is the main protection.

If this produces real `IntegrityError`s under testing, add a focused retry/upsert strategy.

Do not overengineer before observing the problem.

## MEDIUM — detail caching

Details are currently fetched on demand.

Future behavior should likely be:

```text
search
  ↓
save canonical media
  ↓
open card
  ↓
use cached data when fresh
  ↓
refresh provider data when stale/on demand
```

No full catalog caching.

## MEDIUM — only anime/manga are currently exposed by UI

The product vision includes:

```text
anime
manga
manhwa
manhua
novel/ranobe
```

but current UI is primarily:

```text
anime
manga
```

Future support should preferably use a flexible media type taxonomy, not separate tables for every format.

## MEDIUM — Remanga is not implemented

Add it only after current three-provider flow is stable.

---

# 19. NEXT DEVELOPMENT ORDER

This is the current recommended order.

## STEP 1 — Verify migrations

First priority:

```text
0001 → 0002 → 0003
```

against a real PostgreSQL database.

Confirm:

- `media_sources` exists;
- `media.mal_id` is gone after migration;
- old MAL IDs were copied to `media_sources`;
- `genres.mal_id` is gone;
- genre links survive;
- unique constraints exist.

## STEP 2 — Static consistency check

Search the repository for remaining old MAL-centric references such as:

```text
Media.mal_id
Genre.mal_id
media.mal_id
mal_id` used as canonical identity
callbacks containing mal_id
```

Provider-level `mal_id` is allowed when it represents an actual MAL cross-source ID.

The problem is using MAL ID as the internal identity.

## STEP 3 — End-to-end bot test

Test this exact path:

```text
/start
 ↓
Search
 ↓
Anime
 ↓
query
 ↓
results
 ↓
open result
 ↓
card
 ↓
add to library
 ↓
status
 ↓
library
 ↓
change status
 ↓
rate
 ↓
remove
```

Then repeat with manga.

## STEP 4 — Cross-source test

Use a title known to exist in multiple providers.

Verify:

- results are merged when identity is strong;
- `MediaSource` contains multiple IDs;
- only one canonical `Media` is created;
- one library entry is created;
- opening the card can use the stored provider IDs.

## STEP 5 — Improve search

After basic correctness is confirmed:

- improve alternate-name matching;
- improve Russian query handling;
- inspect false merges;
- inspect false duplicates;
- keep matching conservative.

## STEP 6 — Improve media cards

Then add, where providers support it:

- authors;
- studios;
- source links;
- related works;
- better status information;
- richer metadata.

## STEP 7 — Add Remanga

Only after the current architecture is stable.

## STEP 8 — Update README

Once behavior and setup are confirmed.

## STEP 9 — Web App

Only after backend/media/library architecture is stable.

## STEP 10 — Recommendations

Only after enough normalized user/media data exists.

---

# 20. DO NOT DO YET

Do not currently:

- preload huge catalogs;
- build ML recommendations;
- build RPG/gamification systems;
- add complicated progress mechanics;
- split anime/manga/manhwa/manhua into separate database models without need;
- build microservices;
- aggressively fuzzy-merge titles;
- make MAL the canonical identity again;
- build the Web App before the core backend is stable;
- require Docker for every local development task;
- ask the user to manually edit PostgreSQL internals unless absolutely necessary.

---

# 21. CODING / EDITING RULES

The user explicitly wants the assistant to behave as a technical editor.

## Rule 1 — find the concrete problem first

Explain briefly what is wrong and why.

## Rule 2 — preserve logic

Do not rewrite working architecture merely for style.

## Rule 3 — minimal changes

Make the smallest reasonable change that fixes the issue.

## Rule 4 — no unnecessary dependencies

Do not add libraries unless they are actually required.

## Rule 5 — preserve formatting

Use 4-space Python indentation and preserve surrounding formatting where practical.

## Rule 6 — no `...` placeholders

Never give the user code like:

```python
...
```

as a substitute for omitted code.

If a function changes, provide the complete function.

## Rule 7 — prefer exact replacements

When explaining local changes, prefer:

```text
БЫЛО → СТАЛО
```

or provide a complete ready-to-replace function/file when appropriate.

## Rule 8 — do not rewrite huge files unnecessarily

If one or two functions need changes, do not make the user replace a 2500-line file.

## Rule 9 — list multiple problems by priority

Use:

```text
КРИТИЧНО
ВЫСОКИЙ ПРИОРИТЕТ
СРЕДНИЙ
```

## Rule 10 — proceed without unnecessary confirmation

The user explicitly allows the assistant to make reasonable development decisions without asking every time.

If the user says:

```text
давай
делай
продолжай
```

continue with the next logical development step.

Ask only when the missing information genuinely changes the product or makes safe implementation impossible.

---

# 22. GIT WORKFLOW

Repository:

```text
Kerdor/anime_tracker_bot
```

Branch:

```text
main
```

The user expects changes to be committed to GitHub when the assistant has the required tool access.

When changing a file:

1. inspect current version;
2. preserve newer changes;
3. make focused changes;
4. use a meaningful commit message;
5. verify the write succeeded;
6. report the commit.

The user can then update their local clone with:

```bat
git pull
```

If local changes conflict, explain the exact conflict instead of telling the user to delete changes blindly.

---

# 23. LOCAL COMMANDS

Useful commands:

```bat
git status
git pull
git log --oneline -10
tree /F
python --version
python -m pip --version
alembic current
alembic upgrade head
```

The user previously confused:

```text
free /F
```

with:

```text
tree /F
```

This is irrelevant to the project.

---

# 24. WEB APP PLAN

A Telegram Web App is planned as a later stage.

Potential UI:

- dark theme;
- dashboard;
- library tabs;
- search;
- filters;
- title pages;
- profile;
- statistics;
- recommendations;
- infinite scrolling where useful.

The existing `api/` directory is currently only a placeholder.

Do not build the complete Web App yet.

The backend/data model should first become stable enough that both Telegram handlers and future Web App endpoints can reuse the same application logic.

---

# 25. RECOMMENDATION PLAN

Later recommendation phases:

### Phase 1 — content based

```text
ratings
+ genres
+ metadata
→ recommendations
```

### Phase 2 — media similarity

```text
Media A ↔ Media B
```

### Phase 3 — collaborative

```text
similar users
→ titles they liked
→ recommendations
```

Do not implement this before the library/media model has enough real data.

---

# 26. NEW CHAT INSTRUCTIONS

When a new chat continues this project:

1. Read `PROJECT_STATE.md` first.
2. Use the current GitHub repository as the code source of truth.
3. Do not assume the code exactly matches this document if newer commits exist.
4. Check the current branch/commit and relevant files before editing.
5. Do not ask the user to repeat project history already captured here.
6. Preserve the product decisions in this document unless the user explicitly changes them.
7. Do not assume a feature is complete merely because a provider/model/file exists.
8. Verify integration points.
9. Follow the user's coding/editing rules.
10. If the user says `давай`, `делай` or `продолжай`, take the next logical implementation step.
11. Keep explanations concise and practical in Russian.
12. Do not claim real-world runtime success without actual testing.

## Default next action

If asked to continue without a specific task, do this:

```text
1. inspect current repository
2. verify Alembic 0003 against models
3. search for remaining MAL-only identity references
4. fix concrete inconsistencies
5. verify handlers/repository/provider integration
6. then proceed to end-to-end testing
```

---

# 27. IMPORTANT PROJECT SEPARATION

This project is:

```text
Kerdor/anime_tracker_bot
```

Do not confuse it with other projects discussed by the user, especially:

```text
InsaneBot-discord
nightmare_spire_bot
solo_rank_bot
```

Those projects have different architectures and state files.

This `PROJECT_STATE.md` belongs **only** to `anime_tracker_bot`.

---

# 28. CURRENT ONE-LINE SUMMARY

> **Anime Tracker Bot is currently in the middle of a successful migration from a MAL-centric tracker to a canonical multi-source architecture (`Media → MediaSource → UserMedia`); migrations 0001–0003, source-aware repository logic, aggregator search, MangaLib details and canonical Telegram callbacks are in place, and the next priority is real PostgreSQL migration verification plus a full end-to-end search/card/library test before adding more providers or features.**
