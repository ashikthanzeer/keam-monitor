from __future__ import annotations

import logging
import os

from telegram import Message, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.commands import get_latest_update, get_monitor_status
from utils.subscribers import add_subscriber, remove_subscriber

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logger = logging.getLogger(__name__)


def _message(update: Update) -> Message | None:
    """Return the update message, logging when a command cannot be answered."""
    if update.message is None:
        logger.warning("Received Telegram command without a message")
        return None
    return update.message


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe a user and confirm the action."""
    message = _message(update)
    if message is None or update.effective_chat is None:
        return

    chat_id = update.effective_chat.id
    if add_subscriber(chat_id):
        await message.reply_text(
            "\u2705 Welcome to KEAM Monitor!\n\n"
            "You have successfully subscribed to KEAM allotment notifications.\n\n"
            "Use /help to see available commands."
        )
    else:
        await message.reply_text("You are already subscribed.")


async def stop(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe a user and confirm the action."""
    message = _message(update)
    if message is None or update.effective_chat is None:
        return

    chat_id = update.effective_chat.id
    if remove_subscriber(chat_id):
        await message.reply_text("You have been unsubscribed.")
    else:
        await message.reply_text("You are not currently subscribed.")


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available commands."""
    message = _message(update)
    if message is None:
        return

    await message.reply_text(
        "/start - Subscribe to notifications\n"
        "/stop - Unsubscribe from notifications\n"
        "/status - Show monitor status\n"
        "/latest - Show the latest stored update\n"
        "/help - Show this help message"
    )


async def status(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the monitor status and subscriber count."""
    message = _message(update)
    if message is None:
        return

    await message.reply_text(get_monitor_status())


async def latest(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the latest stored monitoring update."""
    message = _message(update)
    if message is None:
        return

    await message.reply_text(get_latest_update())


def build_application() -> Application:
    """Build the Telegram bot application with all command handlers."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("latest", latest))
    return application


def main() -> None:
    """Run the interactive Telegram bot polling loop."""
    app.run_polling()


app = build_application()


if __name__ == "__main__":
    main()
