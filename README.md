# Telegram Reminder Bot

A simple Telegram bot that lets you set, list, and cancel reminders. Reminders are persisted in SQLite and survive restarts.

## Features

- **Set reminders** with relative (`30s`, `5m`, `2h`, `1d`) or absolute (`2025-04-01 14:00`) times
- **List** all your pending reminders
- **Cancel** any reminder by ID
- Reminders are **persisted** in SQLite and automatically rescheduled on bot restart

## Prerequisites

- Python 3.10+
- A Telegram Bot token (create one via [@BotFather](https://t.me/BotFather))

## Setup

1. **Clone the repo and install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set your bot token:**

   ```bash
   export TELEGRAM_BOT_TOKEN="your-bot-token-here"
   ```

   Optionally set a custom database path (defaults to `reminders.db`):

   ```bash
   export REMINDER_DB_PATH="/path/to/reminders.db"
   ```

3. **Run the bot:**

   ```bash
   python bot.py
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and usage |
| `/remind <time> <message>` | Set a reminder |
| `/list` | List your pending reminders |
| `/cancel <id>` | Cancel a reminder by ID |

### Time Formats

- **Relative:** `30s` (30 seconds), `5m` (5 minutes), `2h` (2 hours), `1d` (1 day)
- **Absolute:** `YYYY-MM-DD HH:MM` in UTC (e.g. `2025-04-01 14:00`)

### Examples

```
/remind 30m Buy groceries
/remind 2h Call the dentist
/remind 2025-12-25 09:00 Merry Christmas!
/list
/cancel 3
```

## Project Structure

```
├── bot.py            # Entry point — initializes and starts the bot
├── handlers.py       # Command handlers (start, remind, list, cancel)
├── scheduler.py      # APScheduler wrapper for scheduling reminders
├── db.py             # SQLite database layer (CRUD for reminders)
├── config.py         # Configuration (reads env vars)
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## How It Works

1. When a user sends `/remind 30m Buy groceries`, the bot parses the time, stores the reminder in SQLite, and schedules an APScheduler job.
2. When the scheduled time arrives, the bot sends the user a message and deletes the reminder from the database.
3. On restart, all pending reminders are loaded from SQLite and rescheduled automatically.
