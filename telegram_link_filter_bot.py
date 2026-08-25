import os
import re
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─── Configuration ───────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"

# Regex that matches most URLs / t.me links
LINK_PATTERN = re.compile(
    r"(?:https?://"              # http:// or https://
    r"|t\.me/"                   # telegram short links
    r"|(?:www\.))",              # www.
    re.IGNORECASE,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Helper: check if user is admin or owner ─────────────────────
async def is_admin_or_owner(context: ContextTypes.DEFAULT_TYPE, chat, user_id: int) -> bool:
    """Return True if user is admin or owner of the chat."""
    member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user_id)
    return member.status in ("administrator", "creator")


# ─── Message handler ─────────────────────────────────────────────
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return

    chat = message.chat
    user_id = message.from_user.id if message.from_user else None

    # Skip if no user (e.g. anonymous admin) or no text / caption
    if user_id is None:
        return

    text = message.text or message.caption or ""

    # Also check URL entities (e.g. previews, text_link)
    for ent in (message.entities or []) + (message.caption_entities or []):
        if ent.type == "text_link" and ent.url:
            text += " " + ent.url
        elif ent.type == "url" and message.text:
            text += " " + message.text[ent.offset : ent.offset + ent.length]
        elif ent.type == "url" and message.caption:
            text += " " + message.caption[ent.offset : ent.offset + ent.length]

    # ── Check 1: does the message contain a link? ──
    if not LINK_PATTERN.search(text):
        return  # no link found, let it stay

    # ── Check 2: is the sender an admin / owner? ──
    try:
        if await is_admin_or_owner(context, chat, user_id):
            return  # admin/owner — allowed
    except Exception as e:
        logger.warning(
            "Could not check member status for %s in %s (%s): %s — attempting deletion",
            user_id, chat.id, chat.title, e,
        )
        # Fall through to attempt deletion — treat unknown users as non-admin.

    # ── Delete the message ──
    try:
        await message.delete()
        logger.info(
            "Deleted link message from user %s in chat %s (%s)",
            user_id,
            chat.id,
            chat.title,
        )
    except Exception as e:
        logger.error(
            "Failed to delete message from %s in %s (%s): %s — "
            "make sure the bot is an admin with 'Delete Messages' permission",
            user_id, chat.id, chat.title, e,
        )


# ─── Main ────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(
            "ERROR: Set BOT_TOKEN env var or edit BOT_TOKEN in the script.\n"
            "  export BOT_TOKEN='your-telegram-bot-token'"
        )
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Listen for any new text/photo/document/video message in groups/channels
    # Caption filtering is handled inside filter_links via message.caption
    app.add_handler(
        MessageHandler(
            filters.ALL
            & ~filters.COMMAND
            & (filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.ANIMATION),
            filter_links,
        )
    )

    # ─── Health check server for Render / hosting platforms ───
    port = int(os.environ.get("PORT", 10000))

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, format, *args):
            pass  # silence request logs

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Health check server on port %s", port)

    logger.info("Bot is running… Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
