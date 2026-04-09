# Uzbek Movie Library Bot (aiogram 3.x)

Telegram bot for movie library management with:
- aiogram 3.x
- PostgreSQL on Railway (`asyncpg`)
- SQLite fallback for local run (`aiosqlite`)
- Full Uzbek interface (messages, menus, buttons)

## Features

- Admin movie upload flow with FSM:
  - video forward/send
  - title
  - optional description (`/skip`)
  - optional preview image (`/skip`)
- Channel announcement post (without sending actual movie file to channel)
- Deep link watch flow: `https://t.me/BOT_USERNAME?start=watch_<number>`
- User commands:
  - `/start`, `/movies`, `/search <query>`, `/movie <number>`
  - sending only number (e.g. `42`) opens movie details
- Admin panel:
  - add/edit/delete movies
  - users list, stats, broadcast
- Inline mode:
  - `@botusername <query>`
  - empty query -> latest 30 movies
  - number query -> exact movie
  - text query -> title search
- Auto DB table creation and missing-column recovery on startup

## Project structure

```
bot.py
app/
  config.py
  db/
    database.py
    models.py
    crud.py
  handlers/
    user.py
    admin.py
    movie_upload.py
    inline.py
  keyboards/
    inline.py
    reply.py
  middlewares/
    auth.py
  utils/
    helpers.py
```

## Local setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create `.env` from `.env.example` and fill values.
3. Run:
   ```bash
   python bot.py
   ```

If `DATABASE_URL` is empty, local `sqlite+aiosqlite:///movies.db` is used.

## Railway deploy

1. Push this repository to GitHub.
2. Connect repository in Railway.
3. Set environment variables in Railway project:
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - `CHANNEL_ID`
   - `BOT_USERNAME`
   - `DATABASE_URL` (`postgresql+asyncpg://...`)
4. Railway starts `python bot.py` via `Procfile`.

## Notes

- Do not use `psycopg2`; this project uses `asyncpg`.
- All user-facing texts are in Uzbek.
