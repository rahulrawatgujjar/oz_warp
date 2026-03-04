import re
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from db import add_reminder, delete_reminder, get_reminders
from scheduler import cancel_scheduled_reminder, schedule_reminder

# --- Time parsing helpers ---------------------------------------------------

_RELATIVE_RE = re.compile(r"^(\d+)([smhd])$")

_UNIT_MAP = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
}


def parse_time(text: str) -> datetime | None:
    """Parse a time string into a UTC datetime.

    Supports:
      - Relative: 30s, 5m, 2h, 1d
      - Absolute: YYYY-MM-DD HH:MM
    Returns None if the format is unrecognised.
    """
    text = text.strip()

    # Relative
    match = _RELATIVE_RE.match(text)
    if match:
        amount = int(match.group(1))
        unit = _UNIT_MAP[match.group(2)]
        return datetime.now(timezone.utc) + timedelta(**{unit: amount})

    # Absolute  (YYYY-MM-DD HH:MM)
    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    return None


# --- Handlers ---------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    text = (
        "\U0001f514 *Reminder Bot*\n\n"
        "I can remind you about things\\!\n\n"
        "*Commands:*\n"
        "`/remind <time> <message>` — Set a reminder\n"
        "`/list` — Show your pending reminders\n"
        "`/cancel <id>` — Cancel a reminder\n\n"
        "*Time formats:*\n"
        "• Relative: `30s`, `5m`, `2h`, `1d`\n"
        "• Absolute: `2025\\-04\\-01 14:00` \\(UTC\\)\n\n"
        "*Examples:*\n"
        "`/remind 30m Buy groceries`\n"
        "`/remind 2h Call the dentist`\n"
        "`/remind 2025\\-12\\-25 09:00 Merry Christmas\\!`"
    )
    await update.message.reply_text(  # type: ignore[union-attr]
        text=text,
        parse_mode="MarkdownV2",
    )


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remind <time> <message>."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Usage: /remind <time> <message>\n"
            "Examples:\n"
            "  /remind 30m Buy groceries\n"
            "  /remind 2025-04-01 14:00 Submit report"
        )
        return

    # Try relative time first (single token)
    time_str = context.args[0]
    remind_at = parse_time(time_str)
    msg_start_index = 1

    # Try absolute time (two tokens: date + time)
    if remind_at is None and len(context.args) >= 3:
        time_str = f"{context.args[0]} {context.args[1]}"
        remind_at = parse_time(time_str)
        msg_start_index = 2

    if remind_at is None:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Could not parse the time. Use formats like:\n"
            "  30s, 5m, 2h, 1d\n"
            "  2025-04-01 14:00"
        )
        return

    message = " ".join(context.args[msg_start_index:])
    if not message:
        await update.message.reply_text("Please provide a reminder message.")  # type: ignore[union-attr]
        return

    if remind_at <= datetime.now(timezone.utc):
        await update.message.reply_text("The reminder time must be in the future.")  # type: ignore[union-attr]
        return

    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    user_id = update.effective_user.id  # type: ignore[union-attr]
    reminder_id = await add_reminder(chat_id, user_id, message, remind_at)

    schedule_reminder(
        context.bot, chat_id, user_id, reminder_id, message, remind_at
    )

    formatted_time = remind_at.strftime("%Y-%m-%d %H:%M UTC")
    await update.message.reply_text(  # type: ignore[union-attr]
        f"✅ Reminder #{reminder_id} set for {formatted_time}\n"
        f"Message: {message}"
    )


async def list_reminders(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /list command."""
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    user_id = update.effective_user.id  # type: ignore[union-attr]
    reminders = await get_reminders(chat_id, user_id)

    if not reminders:
        await update.message.reply_text("You have no pending reminders.")  # type: ignore[union-attr]
        return

    lines = ["📋 *Your reminders:*\n"]
    for r in reminders:
        remind_at = datetime.fromisoformat(r["remind_at"]).strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"• *#{r['id']}* — {remind_at}\n  {r['message']}")

    await update.message.reply_text(  # type: ignore[union-attr]
        "\n".join(lines), parse_mode="Markdown"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel <id>."""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /cancel <reminder_id>")  # type: ignore[union-attr]
        return

    try:
        reminder_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Reminder ID must be a number.")  # type: ignore[union-attr]
        return

    user_id = update.effective_user.id  # type: ignore[union-attr]
    deleted = await delete_reminder(reminder_id, user_id)

    if deleted:
        cancel_scheduled_reminder(reminder_id)
        await update.message.reply_text(f"🗑️ Reminder #{reminder_id} cancelled.")  # type: ignore[union-attr]
    else:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"Reminder #{reminder_id} not found or doesn't belong to you."
        )
