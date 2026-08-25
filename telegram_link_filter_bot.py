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
    r"(?:"
    r"https?://"           # http:// or https://
    r"|t\.me/"             # telegram short links
    r"|www\."              # www.
    r")",
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
    logger.info("User %s status in chat %s: %s", user_id, chat.id, member.status)
    return member.status in ("administrator", "creator")


# ─── Message handler ─────────────────────────────────────────────
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle both regular messages and channel posts
    message = update.effective_message
    if message is None:
        logger.debug("No effective_message in update %s", update.update_id)
        return

    chat = message.chat
    user = message.from_user
    sender_chat = message.sender_chat  # For anonymous admins / channel posts

    logger.info(
        "📩 Message received in '%s' (id=%s, type=%s) from user=%s sender_chat=%s: %s",
        chat.title, chat.id, chat.type,
        user.id if user else "None",
        sender_chat.id if sender_chat else "None",
        (message.text or message.caption or "")[:100],
    )

    # If message is from a channel (sender_chat is the channel itself),
    # skip deletion — this is how admins post in linked groups
    if sender_chat and sender_chat.id == chat.id:
        logger.info("Message from the channel/group itself (sender_chat == chat), skipping.")
        return

    # If sent by a channel linked to this group, check if it's the owner channel
    if sender_chat and not user:
        logger.info("Anonymous sender_chat %s (%s) — attempting deletion.",
                     sender_chat.id, sender_chat.title)
        # Anonymous sender — can't check admin status, so check for links and delete
        user_id = None
    elif user:
        user_id = user.id
    else:
        logger.info("No user and no sender_chat, skipping.")
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

    logger.info("Extracted text for link check: %s", text[:200])

    # ── Check 1: does the message contain a link? ──
    if not LINK_PATTERN.search(text):
        logger.info("No link found in message, allowing.")
        return  # no link found, let it stay

    logger.info("⚠️ Link detected in message!")

    # ── Check 2: is the sender an admin / owner? ──
    if user_id is not None:
        try:
            if await is_admin_or_owner(context, chat, user_id):
                logger.info("User %s is admin/owner, allowing link.", user_id)
                return  # admin/owner — allowed
            logger.info("User %s is NOT admin/owner, will delete.", user_id)
        except Exception as e:
            logger.warning(
                "Could not check member status for %s in %s (%s): %s — attempting deletion",
                user_id, chat.id, chat.title, e,
            )
            # Fall through to attempt deletion — treat unknown users as non-admin.
    else:
        logger.info("No user_id (anonymous), will attempt deletion.")

    # ── Delete the message ──
    try:
        await message.delete()
        logger.info(
            "✅ DELETED link message from user %s in chat %s (%s)",
            user_id, chat.id, chat.title,
        )
    except Exception as e:
        logger.error(
            "❌ Failed to delete message from %s in %s (%s): %s — "
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

    # Filter for content types we want to check
    content_filter = (
        filters.ALL
        & ~filters.COMMAND
        & (filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.ANIMATION)
    )

    # Listen for regular messages in groups
    app.add_handler(
        MessageHandler(content_filter, filter_links)
    )

    # Also listen for channel_post (messages forwarded from linked channels)
    app.add_handler(
        MessageHandler(content_filter, filter_links),
        group=1,  # Different handler group
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
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
