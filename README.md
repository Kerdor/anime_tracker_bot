# Anime Tracker Bot

Telegram bot for tracking anime, manga, manhwa, manhua and novels.

## Stack

- Python
- aiogram
- FastAPI
- PostgreSQL
- SQLAlchemy
- Jikan API / MyAnimeList data

## Development

1. Create `.env` from `.env.example`.
2. Start PostgreSQL:

```bash
docker compose up -d
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the bot:

```bash
python main.py
```

The project is currently at the initial foundation stage. Database models, Jikan integration and bot handlers will be added incrementally.
