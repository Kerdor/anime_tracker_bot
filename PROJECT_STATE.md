# PROJECT STATE — Anime Tracker Bot

> **Purpose:** This file is the canonical handoff/context document for continuing development of `anime_tracker_bot` from a new chat.
>
> **IMPORTANT:** A new chat should read this file first and treat it as the primary project context. Do not make the user repeat the project history unless something genuinely contradicts this file or the current repository state.

---

## 0. CURRENT STATE — START HERE

### Project

Telegram bot for tracking anime, manga, manhwa, manhua, novels/ranobe and potentially other media types.

Repository:

- `https://github.com/Kerdor/anime_tracker_bot`

Default branch:

- `main`

The repository was cloned locally by the user into:

- `C:\Users\nik_s\OneDrive\Рабочий стол\ALL\it\projects\python\tg\anime_tracker_bot`

At the time of the handoff the local clone reported:

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

Python:

```text
Python 3.12.10
```

pip:

```text
pip 26.1.2
```

Alembic is installed globally and the command works, but `alembic current` currently cannot start because the project requires `BOT_TOKEN` and `DATABASE_URL` from `.env`.

Docker is **not installed** on the user's machine. Do not assume Docker is available. The project currently documents PostgreSQL through Docker Compose, but the user is not comfortable with Docker/DB terminology and should not be burdened with it unless necessary.

### Immediate architectural goal

The project is currently being evolved from a simple MAL/Jikan tracker into a **multi-source media tracker**.

The intended source architecture is:

```text
                         ┌── Shikimori
                         │
Telegram search ──→ MediaAggregator ──┼── MangaLib
                         │
                         ├── MAL / Jikan
                         │
                         └── Remanga (planned)
                                  │
                                  ↓
                         Unified media result
                                  │
                                  ↓
                         Internal Media entity
                                  │
                                  ├── MediaSource(s)
                                  └── UserMedia
```

The important design decision is:

**Sources are providers of data, not separate user libraries.**

One real-world title should correspond to one internal `Media` entity, with multiple external source identifiers stored in `MediaSource`.

This is specifically intended to prevent duplicates when the same title exists on MAL, Shikimori, MangaLib, etc.

### Current highest-priority task

Finish the transition to a proper internal media model and integrate the multi-source aggregator into the actual bot flow.

The current repository contains pieces of this architecture, but they are not yet fully wired together. Do NOT assume that merely having `MediaAggregator`, `MediaSource`, Shikimori or MangaLib files means the whole feature is complete.

---

# 1. PROJECT VISION

The bot is intended to become a polished Telegram tracker where a user can:

- search anime;
- search manga;
- search manhwa;
- search manhua;
- search novels/ranobe;
- add titles to a personal library;
- assign a status;
- rate titles from 1 to 10;
- browse library sections;
- view statistics/profile;
- eventually receive recommendations;
- eventually use a Telegram Web App for a much richer UI.

The user wants a **cool, polished, dark-themed product**, not just a primitive command bot.

The first interface should support both:

- ordinary Telegram commands/messages;
- inline buttons;
- eventually a Telegram Web App.

The user agreed that the project can initially support Russian only, with the architecture prepared so additional languages can be added later.

---

# 2. PRODUCT DECISIONS ALREADY MADE

## 2.1 Language

Initial language:

- Russian (`ru`)

Future:

- English and potentially other languages should be possible without redesigning the whole project.

A `language` field already exists on `User` with default `ru`.

## 2.2 Visual style

Desired UI:

- dark;
- modern;
- clean;
- visually attractive;
- eventually especially polished in the Web App.

## 2.3 Library statuses

Current status set:

```text
planning   = 🟡 Хочу
watching   = 🔵 Смотрю / Читаю
completed  = 🟢 Завершено
paused     = ⚪ На паузе
dropped    = 🔴 Брошено
```

The user explicitly said that **status is enough for the first version**. Do not invent a complicated progress system unless explicitly requested later.

## 2.4 Rating

Rating scale:

- 1–10

The user wants users to be able to rate titles.

## 2.5 Database philosophy

The user initially said they do **not** want to maintain a huge hand-built database of 100k+ anime and even larger manga/manhwa/etc. catalogs.

Therefore:

- external providers should supply catalog data;
- our database should primarily store normalized/cached media entities and user data;
- do not attempt to preload the entire external catalog into PostgreSQL;
- data should be fetched/searchable from external providers and saved when useful.

## 2.6 Scale

Initial expected scale:

- several hundred users.

Architecture should not unnecessarily prevent:

- thousands of users.

Do not overengineer for millions yet, but avoid obviously single-user/stateful architecture.

## 2.7 Recommendations

Recommendation system is planned but **not the current task**.

Future recommendations should be based on user library/ratings/statuses and normalized media metadata.

This is one reason the unified `Media` model is important.

---

# 3. EXTERNAL DATA SOURCES

The user proposed using several sources rather than relying only on MAL:

- Shikimori;
- MangaLib;
- Remanga;
- MAL/Jikan;
- potentially additional sources later.

## 3.1 MAL / Jikan

Current provider:

- `providers/jikan.py`

Jikan is the MAL API provider.

Current provider name:

```text
mal
```

Jikan is valuable for:

- large global catalog;
- MAL IDs;
- English/Japanese titles;
- scores;
- anime/manga metadata;
- relations and other future metadata.

Current search endpoint behavior:

- anime → `/anime`
- manga → `/manga`

Current search limit:

- 25

Current `JikanClient` also normalizes title strings and ranks search results by:

1. exact title match;
2. contains match;
3. word overlap;
4. MAL score as a secondary ranking factor.

Important current limitation:

**Jikan does not guarantee that a Russian title exists or that a Russian query will always find the desired title.**

Therefore MAL/Jikan alone should NOT be treated as the final Russian search solution.

## 3.2 Shikimori

Current provider:

- `providers/shikimori.py`

Provider name:

```text
shikimori
```

Current default API base:

```text
https://shikimori.one/api
```

Search endpoints:

- anime → `/animes`
- manga → `/mangas`

Search uses `search` and `limit` parameters.

Shikimori data is particularly valuable because it exposes Russian title information through `russian`.

The parser currently prefers the Russian title when available.

It also extracts:

- Shikimori ID;
- MAL ID when supplied by Shikimori;
- title;
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

Current provider:

- `providers/mangalib.py`

Provider name:

```text
mangalib
```

Current default base URL:

```text
https://mangalib.me
```

The current implementation searches `/search` with:

```text
 type=manga
 q=<query>
```

The parser knows about fields such as:

- `rus_name`;
- `name`;
- `eng_name`;
- `otherNames`;
- `id`;
- `slug`;
- `cover`;
- `releaseDate`;
- `summary`.

MangaLib is especially valuable for Russian-language manga/manhwa/manhua/etc. discovery.

Current limitation:

- `get_media()` is not implemented and currently returns `None`.

This must be fixed before treating MangaLib as a fully supported detail provider.

## 3.4 Remanga

Remanga was explicitly proposed as another Russian-language source.

At the time of this state document, Remanga is **planned, not fully integrated**.

Do not claim that Remanga is already implemented unless the repository has subsequently added a working provider.

---

# 4. SEARCH REQUIREMENTS

This is one of the most important product features.

The user explicitly wants searches such as:

```text
Розовая пора моей школьной жизни сплошной обман
Как и ожидалось, моя школьная жизнь...
Oregairu
Yahari Ore no Seishun Love Comedy wa Machigatteiru
```

to find the same title where appropriate.

Therefore search should support:

- Russian names;
- English names;
- original/Japanese names;
- alternate names;
- abbreviated names;
- punctuation differences;
- `ё` vs `е`;
- differences in capitalization;
- reasonable word overlap.

The current normalizer lowercases text, replaces `ё` with `е`, removes punctuation and collapses whitespace.

### Important search architecture

The correct long-term flow is:

```text
user query
    ↓
normalize query
    ↓
parallel provider searches
    ↓
collect results
    ↓
normalize titles
    ↓
identity matching / deduplication
    ↓
merge metadata
    ↓
rank unified results
    ↓
show user
```

Do not simply show separate MAL/Shikimori/MangaLib results for the same title.

---

# 5. MEDIA AGGREGATOR

Current file:

- `providers/aggregator.py`

Current class:

```python
MediaAggregator
```

It currently instantiates:

```text
JikanClient()
ShikimoriClient()
MangaLibClient()
```

and runs provider searches concurrently using `asyncio.gather(..., return_exceptions=True)`.

This means one provider failure should not destroy the whole search result.

Current aggregator functionality:

- normalize titles;
- calculate search relevance;
- collect provider/provider IDs;
- merge exact provider identity matches;
- merge MAL IDs where available;
- perform a second title-based deduplication pass;
- merge title variants/providers/source IDs;
- rank by search score and external score.

Current result metadata includes concepts such as:

```text
provider
provider_id
mal_id
providers
source_ids
search_score
```

### Important limitation

The current deduplication is still not a perfect cross-provider entity-resolution system.

It is safe to match on strong external identity information, but **do not aggressively fuzzy-merge unrelated works** just because their names look similar.

A wrong merge is worse than a duplicate.

Future entity resolution should preferably use:

1. shared external IDs / known cross-links;
2. strong normalized title matches;
3. type/year/other metadata where useful;
4. conservative fuzzy matching only when confidence is high.

---

# 6. CURRENT DATABASE MODEL

Current file:

- `database/models.py`

Current models:

```text
User
Media
MediaSource
UserMedia
Genre
MediaGenre
```

## 6.1 User

Fields include:

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

## 6.2 Media

Current fields include:

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

- `sources` → `MediaSource`
- `library_entries` → `UserMedia`
- `genres` → `Genre`

### Important

The intended architecture is that `Media` is the internal canonical entity.

It should NOT be tied to only MAL.

## 6.3 MediaSource

Current model:

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

This is the key model for multi-source support.

Example:

```text
Media #42
  ├── mal       = 12345
  ├── shikimori = 67890
  └── mangalib  = 55555
```

All three should refer to the same internal `Media` when we know they represent the same work.

## 6.4 UserMedia

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

This is the user's personal library relation.

## 6.5 Genre / MediaGenre

`Genre` currently has:

```text
id
mal_id
name
```

`MediaGenre` is the many-to-many association.

### Future consideration

The `Genre.mal_id` design is currently MAL-centric and may need to be generalized if genre information from multiple sources becomes important.

Do not redesign this casually; preserve working behavior until there is a clear need.

---

# 7. DATABASE / ALEMBIC STATUS

Current migration directory:

```text
alembic/
└── versions/
    └── 0001_initial.py
```

Current Alembic head:

```text
0001_initial
```

The project uses:

- PostgreSQL;
- SQLAlchemy;
- Alembic.

`README.md` currently documents PostgreSQL via Docker Compose.

### User environment

Docker is NOT installed on the user's Windows machine.

The user is not experienced with database administration and does not understand terms such as migrations intuitively.

When guiding the user:

- explain only what is necessary;
- give exact commands;
- do not make them manually edit database internals unless unavoidable;
- never ask them to paste secrets;
- do not assume Docker is installed.

### `.env`

The current `config.py` requires at least:

```text
BOT_TOKEN
DATABASE_URL
```

The user currently has `.env.example` but has not yet completed a local runnable database environment.

Do not ask the user to send the real bot token.

---

# 8. CURRENT PROJECT STRUCTURE

At the time of handoff:

```text
anime_tracker_bot/
│   .env.example
│   .gitignore
│   alembic.ini
│   config.py
│   docker-compose.yml
│   main.py
│   README.md
│   requirements.txt
│
├───alembic
│   │   env.py
│   │   script.py.mako
│   │   __init__.py
│   │
│   └───versions
│           0001_initial.py
│
├───api
│       __init__.py
│
├───bot
│       handlers.py
│       keyboards.py
│       library.py
│       profile.py
│       __init__.py
│
├───database
│       base.py
│       models.py
│       repository.py
│       session.py
│       __init__.py
│
└───providers
        aggregator.py
        base.py
        jikan.py
        mangalib.py
        shikimori.py
        __init__.py
```

This structure is intentionally simple for now.

Do not split the project into dozens of layers just for theoretical architecture.

---

# 9. CURRENT BOT UI

Current main menu concepts include:

```text
🎬 Аниме
📚 Манга
🔎 Поиск
👤 Мой профиль
📊 Статистика
```

The library has sections:

- anime;
- manga.

Status filters:

- all;
- completed;
- watching;
- planning;
- paused;
- dropped.

Library entries have controls for:

- changing status;
- rating 1–10;
- removing from library;
- returning to library.

Search result UI has pagination support.

### Important current limitation

The existing `bot/handlers.py` still contains direct Jikan/MAL-specific behavior in places.

In particular, current handler logic uses:

```python
from providers.jikan import JikanClient
```

and helper/callback flows based on `mal_id`.

Therefore the aggregator and `MediaSource` architecture is **not yet fully wired into all handlers**.

This is one of the next major implementation tasks.

---

# 10. CURRENT PROFILE / STATISTICS

A profile/statistics feature was started.

The intended information includes:

- user identity;
- total library size;
- anime count;
- manga count;
- average user rating;
- distribution by status.

This is intentionally simple at first.

Future profile/statistics ideas can include:

- completed count;
- time watched/read when reliable data exists;
- genre distribution;
- yearly activity;
- favorite genres;
- rating distribution;
- progress charts.

Do not overbuild statistics before the core library/search architecture is stable.

---

# 11. IMPORTANT CURRENT INCONSISTENCIES / TECHNICAL DEBT

These are important and should be addressed systematically.

## CRITICAL — handlers are still MAL/Jikan-centric

Some callback data and lookup functions still use:

```text
mal_id
```

and direct `JikanClient` loading.

The desired architecture is:

```text
provider-specific search result
        ↓
canonical Media
        ↓
MediaSource IDs
        ↓
UserMedia references Media
```

Handlers should eventually operate on internal `media_id` or a safe source-independent identifier, not assume every title has a MAL ID.

## CRITICAL — migration is not yet complete

`MediaSource` exists in the model, but the database migration history currently only has `0001_initial`.

A proper Alembic migration must be created for the new schema if the initial migration does not already contain the current tables.

Before writing a migration:

1. inspect `0001_initial.py`;
2. compare it to `database/models.py`;
3. determine whether the existing migration already contains `MediaSource`;
4. preserve existing data if any;
5. only then create the next migration.

Do NOT blindly drop/recreate the database.

## HIGH — repository layer needs to match current model

`database/repository.py` must be checked carefully against the current `Media` model.

Especially verify:

- old `Media.mal_id` references;
- `MediaSource` lookup;
- save/upsert behavior;
- library lookup behavior;
- genre handling;
- compatibility with non-MAL titles.

Do not assume a previously drafted repository implementation is correct until it has been inspected against the actual repository.

## HIGH — MangaLib details are incomplete

`MangaLibClient.get_media()` currently returns `None`.

This means MangaLib can currently participate in search but cannot yet be treated as a complete source for detailed media cards.

## HIGH — source-independent callback IDs

Current callback patterns include values such as:

```text
media:<type>:<mal_id>
library_media:<type>:<mal_id>
add:<type>:<mal_id>
status:<type>:<mal_id>:<status>
```

These should eventually be changed to internal media IDs or another stable canonical identifier.

Otherwise titles that exist only on MangaLib/Shikimori cannot be handled correctly.

## MEDIUM — media type vocabulary

Current bot UI primarily distinguishes:

```text
anime
manga
```

The product vision includes:

- anime;
- manga;
- manhwa;
- manhua;
- ranobe/novel;
- potentially other types.

Do not blindly make each of these a separate database table. Prefer a flexible `Media.type` or normalized type taxonomy.

## MEDIUM — genre IDs are MAL-specific

`Genre.mal_id` assumes MAL is the source of genre identity.

This is acceptable temporarily but is not ideal for a multi-source architecture.

## MEDIUM — external data caching strategy

Eventually the bot should avoid repeatedly downloading the same details from providers for every click.

A sensible strategy is:

- search externally;
- save canonical media when user selects/adds it;
- refresh metadata periodically or on demand;
- keep source IDs in `MediaSource`.

Do not cache the entire external catalogs.

---

# 12. TARGET ARCHITECTURE

The desired architecture is approximately:

```text
Telegram / Web App
        │
        ▼
      Handlers / API
        │
        ▼
   Application services
        │
        ├───────────────┐
        ▼               ▼
MediaAggregator    Library service
        │               │
        ├── Jikan       ▼
        ├── Shikimori Database
        ├── MangaLib
        └── Remanga
```

The database should conceptually contain:

```text
User
  │
  └── UserMedia ─────── Media
                           │
                           ├── MediaSource (MAL)
                           ├── MediaSource (Shikimori)
                           ├── MediaSource (MangaLib)
                           └── MediaSource (Remanga)
```

This gives us:

- one user library entry per canonical media entity;
- multiple external IDs per entity;
- provider independence;
- easier future recommendations;
- easier provider replacement/addition;
- fewer duplicate titles.

---

# 13. FUTURE WEB APP

The user thinks a Telegram Web App would be cool.

The intended product can eventually provide:

- dark UI;
- home dashboard;
- library tabs;
- search;
- title cards;
- filters;
- profile;
- statistics;
- recommendations;
- sorting;
- maybe infinite scrolling.

The Telegram bot itself should remain useful without the Web App.

The backend should therefore be designed so both Telegram handlers and the Web App can use the same application/data layer.

The repository already has:

```text
api/
```

but it is currently essentially empty.

Do not build the full Web App before the canonical media/search/library architecture is stable.

---

# 14. FUTURE RECOMMENDATION SYSTEM

This is planned for a later phase.

Possible inputs:

- user ratings 1–10;
- completed titles;
- watching/reading titles;
- dropped titles;
- planned titles;
- genres;
- studios/authors;
- related/franchise data;
- similarity between titles;
- potentially community behavior after enough users exist.

A likely evolution:

### Phase 1
Content-based recommendations:

```text
user ratings + genres + metadata
```

### Phase 2
Similarity between media:

```text
Media A ↔ Media B
```

### Phase 3
Collaborative recommendations:

```text
users with similar tastes
        ↓
what they liked
        ↓
recommendations
```

Do not implement machine learning prematurely.

The normalized `Media` + `UserMedia` data model is the important prerequisite.

---

# 15. DEVELOPMENT RULES FOR THIS PROJECT

These rules reflect the user's explicit preferences when editing code.

## 15.1 Preserve existing logic

Act as a technical editor, not as someone rewriting the project for fun.

When fixing a bug:

1. identify the concrete problem;
2. explain it briefly;
3. make the smallest necessary change;
4. preserve architecture unless there is a real reason to change it;
5. preserve variable/function names when practical;
6. preserve function order;
7. preserve formatting/indentation;
8. do not add unnecessary libraries;
9. do not add speculative checks everywhere.

## 15.2 Never use `...` as a code replacement

When giving code to the user, never write:

```python
...
```

as a placeholder for omitted code.

If a function changes, provide the **complete function**.

## 15.3 Prefer exact replacement fragments

When working with the user locally, prefer:

```text
БЫЛО → СТАЛО
```

or provide the complete file only when the whole file genuinely needs replacement.

Do not make the user manually reconstruct a 2500-line file for a two-function fix.

## 15.4 If multiple problems exist

List them and mark important ones:

```text
КРИТИЧНО
ВЫСОКИЙ ПРИОРИТЕТ
СРЕДНИЙ
```

## 15.5 Do not ask unnecessary questions

The user explicitly said:

> можешь делать не спрашивая меня

Therefore, if a reasonable implementation decision is possible, make it yourself.

Ask only when a decision genuinely changes the product direction or when required information is unavailable.

---

# 16. GIT WORKFLOW

The user is comfortable running simple Git commands but is not an expert.

Repository is:

`Kerdor/anime_tracker_bot`

The user expects the assistant to make changes to GitHub when possible.

When making changes through GitHub tools:

- inspect the current file first;
- preserve the latest version;
- make focused commits;
- use meaningful commit messages;
- do not claim a change was made if the write failed;
- do not silently overwrite unknown newer changes.

The user may then run:

```bat
git pull
```

locally.

If there are local changes, explain the conflict clearly instead of telling the user to delete things blindly.

---

# 17. LOCAL ENVIRONMENT NOTES

Windows CMD is being used.

Example local project directory:

```text
C:\Users\nik_s\OneDrive\Рабочий стол\ALL\it\projects\python\tg\anime_tracker_bot
```

Useful commands:

```bat
git status
git pull
git log --oneline -10
tree /F
python --version
python -m pip --version
```

The user accidentally typed:

```bat
free /F
```

when intending:

```bat
tree /F
```

This is irrelevant to the project and should not be treated as a project issue.

Docker is unavailable locally at present.

---

# 18. README STATUS

Current README describes the project as:

> Telegram bot for tracking anime, manga, manhwa, manhua and novels.

Current stack documented:

- Python
- aiogram
- FastAPI
- PostgreSQL
- SQLAlchemy
- Jikan API / MyAnimeList data

The README currently says the project is at the initial foundation stage, but the actual repository has already progressed beyond that description.

The README should eventually be updated to reflect:

- multi-source architecture;
- Shikimori/MangaLib;
- database model;
- setup without assuming Docker;
- bot commands/features;
- development workflow.

Do this after the architecture stabilizes rather than repeatedly rewriting it during every small change.

---

# 19. IMPLEMENTATION ROADMAP

## Phase 0 — stabilize current foundation

- [x] repository created;
- [x] Python/aiogram foundation;
- [x] SQLAlchemy models started;
- [x] Alembic configured;
- [x] Jikan provider;
- [x] Shikimori provider started;
- [x] MangaLib provider started;
- [x] MediaAggregator started;
- [x] MediaSource model started;
- [x] library UI;
- [x] status system;
- [x] rating 1–10;
- [x] profile/statistics foundation;
- [x] search pagination foundation.

## Phase 1 — canonical media architecture

**CURRENT PRIORITY**

- [ ] inspect `alembic/versions/0001_initial.py` against `database/models.py`;
- [ ] create required migration(s) safely;
- [ ] ensure existing MAL data can be migrated to `MediaSource`;
- [ ] remove assumptions that every `Media` has a MAL ID;
- [ ] update repository functions;
- [ ] update handlers to use internal media IDs/source IDs;
- [ ] make `save_media()` source-aware;
- [ ] make library lookups source-independent;
- [ ] ensure duplicate `(source, source_id)` cannot be created;
- [ ] test add/status/rating/remove flows.

## Phase 2 — real multi-source search

- [ ] integrate `MediaAggregator` into handlers;
- [ ] remove direct Jikan-only search path;
- [ ] show unified results;
- [ ] show Russian title when available;
- [ ] collect alternate names;
- [ ] improve entity resolution;
- [ ] implement MangaLib detail fetching;
- [ ] add Remanga provider;
- [ ] verify provider failures do not break search;
- [ ] add reasonable provider timeouts/retry behavior without overengineering.

## Phase 3 — media details

- [ ] canonical media card;
- [ ] source links;
- [ ] genres;
- [ ] year;
- [ ] score;
- [ ] episode/chapter/volume information;
- [ ] authors/studios;
- [ ] related titles;
- [ ] refresh metadata.

## Phase 4 — library quality

- [ ] source-independent library entries;
- [ ] better filtering;
- [ ] sorting;
- [ ] pagination/infinite scroll where appropriate;
- [ ] better empty states;
- [ ] duplicate protection;
- [ ] statistics improvements.

## Phase 5 — Web App

- [ ] FastAPI endpoints;
- [ ] Telegram Web App authentication;
- [ ] dark UI;
- [ ] library dashboard;
- [ ] search;
- [ ] title pages;
- [ ] filters;
- [ ] profile/statistics.

## Phase 6 — recommendations

- [ ] content-based recommendations;
- [ ] title similarity;
- [ ] personalized ranking;
- [ ] later collaborative filtering if enough data exists.

---

# 20. THINGS WE SHOULD NOT DO YET

Do NOT currently:

- preload 100k+ anime/manga records;
- build ML recommendations;
- build a complex achievement/RPG system;
- add unnecessary gamification;
- split every media type into separate tables;
- create dozens of microservices;
- require Docker just to test a simple bot if a simpler local DB workflow can be provided;
- aggressively fuzzy-merge titles;
- make MAL the permanent canonical identity;
- make the Web App before the backend/media model is stable.

The user wants a powerful product eventually, but the foundation should remain understandable and maintainable.

---

# 21. USER'S ORIGINAL PRODUCT PREFERENCES

These are product decisions from the planning discussion:

- Main language initially Russian.
- Dark visual design.
- Sections rather than one giant undifferentiated list.
- Statuses are enough initially.
- Rating 1–10.
- External catalogs are preferred over maintaining a manually curated giant database.
- MAL is useful, but Russian-language sources such as Shikimori/MangaLib/Remanga are important.
- The bot should eventually support both Telegram UI and Web App.
- Initial scale: hundreds of users, architecture should be able to grow to thousands.
- Recommendations are wanted later, after the core tracker works.

---

# 22. NEW-CHAT HANDOFF INSTRUCTIONS

If a new chat starts with this project, the assistant should:

1. Read `PROJECT_STATE.md`.
2. Open the current repository files before modifying anything.
3. Compare the actual repository with this document because the repository may have advanced since this file was written.
4. Treat the actual repository as authoritative for code state.
5. Treat this document as authoritative for product decisions and historical context unless the user explicitly changes them.
6. Do not ask the user to explain the entire project again.
7. Do not assume a feature is complete just because a file exists.
8. Check integration points before claiming a feature works.
9. Preserve the user's coding preferences listed above.
10. When changing code, explain the concrete problem briefly and make the smallest reasonable change.
11. If the user says `давай`, `делай`, or similar in this project context, proceed with the next logical implementation step rather than asking unnecessary confirmation.
12. Keep the user informed in short, practical Russian.

### If the user asks "продолжай"

The default next action should be to inspect the current repository and continue from the highest-priority unchecked item in the roadmap.

### Current highest-priority implementation order

```text
1. Inspect 0001_initial.py
2. Reconcile DB migration with current models
3. Fix repository/model mismatch
4. Remove MAL-only assumptions from handlers
5. Switch handlers to canonical Media IDs
6. Integrate MediaAggregator into actual search
7. Make source-aware media detail loading
8. Complete MangaLib details
9. Add Remanga
10. Test end-to-end search → card → library → status → rating
```

---

# 23. IMPORTANT CORRECTION FROM PREVIOUS CHAT

Earlier in development, there was confusion between the user's other repository `InsaneBot-discord` and this project.

**Do not use `InsaneBot-discord/PROJECT_STATE.md` as the state file for this project.**

This file belongs specifically to:

```text
Kerdor/anime_tracker_bot
```

The `InsaneBot-discord` project is unrelated to the architecture described here.

---

# 24. FINAL PRINCIPLE

The core idea of the project is:

> **Build a high-quality personal media tracker on top of several external catalogs, while keeping our own database small, canonical, user-centric and source-independent.**

The external services provide catalog knowledge.

Our application provides:

- identity normalization;
- search aggregation;
- user library;
- statuses;
- ratings;
- statistics;
- future recommendations;
- future Web App experience.

That separation is the central architectural decision and should be preserved as the project grows.
