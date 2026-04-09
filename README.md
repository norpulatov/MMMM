# Telegram Movie Library Bot (aiogram 3.x)

English-only Telegram bot that stores a movie library and lets users watch videos via deep links.

## Features

- Admin upload flow (forwarded video -> title -> description optional -> preview optional).
- Channel announcement post with `▶️ Watch` deep link.
- User commands: `/start`, `/movies`, `/search`, `/movie`, numeric movie lookup.
- Watch flow sends the real video file in private chat and increments views.
- Admin tools: `/admin`, `/stats`, `/users`, `/broadcast` (reply-based broadcast).
- Inline mode: `@botusername <query>`.
- Async SQLAlchemy with PostgreSQL (Railway) or SQLite fallback.

## Project Structure

```text
.
├─ bot.py
├─ requirements.txt
├─ railway.json
├─ nixpacks.toml
├─ Procfile
├─ .env.example
└─ app
   ├─ config.py
   ├─ logging_setup.py
   ├─ middlewares.py
   ├─ db
   │  ├─ base.py
   │  ├─ models.py
   │  ├─ repo.py
   │  └─ session.py
   ├─ handlers
   │  ├─ __init__.py
   │  ├─ user.py
   │  ├─ admin.py
   │  └─ inline_mode.py
   ├─ keyboards
   │  └─ common.py
   ├─ states
   │  └─ upload.py
   └─ utils
      └─ formatters.py
```

## Environment

Copy `.env.example` to `.env` and set:

- `BOT_TOKEN`
- `ADMIN_IDS` (comma-separated integers)
- `CHANNEL_ID` (e.g. `-1001234567890`)
- `DATABASE_URL` (PostgreSQL URL for Railway, or leave empty for SQLite fallback)
- `BOT_USERNAME` (without `@`)

If `DATABASE_URL` is empty, bot uses:

`sqlite+aiosqlite:///./movies.db`

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

## Railway Deployment

- `Procfile` uses: `worker: python bot.py`
- `railway.json` starts `python bot.py`
- `nixpacks.toml` pins Python 3.11 for compatibility
- Set Railway variables from `.env.example`

## Notes

- Add bot as admin in your channel so it can publish announcements.
- Announcement post contains metadata and deep link only; video file stays private.
