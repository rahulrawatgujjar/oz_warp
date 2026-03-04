import aiosqlite
from datetime import datetime, timezone

from config import DATABASE_PATH


async def init_db() -> None:
    """Create the reminders table if it does not exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                message    TEXT    NOT NULL,
                remind_at  TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            )
            """
        )
        await db.commit()


async def add_reminder(
    chat_id: int, user_id: int, message: str, remind_at: datetime
) -> int:
    """Insert a new reminder and return its ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (chat_id, user_id, message, remind_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                chat_id,
                user_id,
                message,
                remind_at.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def get_reminders(chat_id: int, user_id: int) -> list[dict]:
    """Return all pending reminders for a user in a chat."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, message, remind_at FROM reminders "
            "WHERE chat_id = ? AND user_id = ? ORDER BY remind_at",
            (chat_id, user_id),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_reminder(reminder_id: int, user_id: int) -> bool:
    """Delete a reminder by ID (only if it belongs to the user). Returns True if deleted."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_all_pending_reminders() -> list[dict]:
    """Return all reminders that haven't fired yet (for rescheduling on startup)."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, chat_id, user_id, message, remind_at FROM reminders "
            "WHERE remind_at > ? ORDER BY remind_at",
            (now,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
