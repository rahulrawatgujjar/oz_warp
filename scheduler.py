import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from db import delete_reminder, get_all_pending_reminders

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Return the singleton scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


async def fire_reminder(
    bot: Bot, chat_id: int, user_id: int, reminder_id: int, message: str
) -> None:
    """Send the reminder message and remove it from the database."""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"\u23f0 *Reminder:* {message}",
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Failed to send reminder %s", reminder_id)
    finally:
        await delete_reminder(reminder_id, user_id)


def schedule_reminder(
    bot: Bot,
    chat_id: int,
    user_id: int,
    reminder_id: int,
    message: str,
    remind_at: datetime,
) -> None:
    """Add a one-shot job to the scheduler."""
    scheduler = get_scheduler()
    scheduler.add_job(
        fire_reminder,
        trigger="date",
        run_date=remind_at,
        args=[bot, chat_id, user_id, reminder_id, message],
        id=f"reminder_{reminder_id}",
        replace_existing=True,
    )


def cancel_scheduled_reminder(reminder_id: int) -> None:
    """Remove a scheduled job if it exists."""
    scheduler = get_scheduler()
    job_id = f"reminder_{reminder_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def reschedule_pending_reminders(bot: Bot) -> None:
    """Reload all pending reminders from the DB and schedule them."""
    reminders = await get_all_pending_reminders()
    now = datetime.now(timezone.utc)
    for r in reminders:
        remind_at = datetime.fromisoformat(r["remind_at"])
        if remind_at.tzinfo is None:
            remind_at = remind_at.replace(tzinfo=timezone.utc)
        if remind_at <= now:
            # Already past — fire immediately
            await fire_reminder(bot, r["chat_id"], r["user_id"], r["id"], r["message"])
        else:
            schedule_reminder(
                bot, r["chat_id"], r["user_id"], r["id"], r["message"], remind_at
            )
    logger.info("Rescheduled %d pending reminders", len(reminders))
