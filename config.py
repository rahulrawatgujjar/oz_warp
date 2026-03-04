import os

TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DATABASE_PATH: str = os.environ.get("REMINDER_DB_PATH", "reminders.db")
