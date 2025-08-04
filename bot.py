# bot.py

import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# --- Configuration (Unchanged) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("No WEBHOOK_URL found in environment variables")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello, {user.full_name}!\n\nI am an advanced Id Extractor Bot.\n\nType /help to see everything I can do!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "ℹ️ **Here's what I can do:**\n\n"
        "🔹 `/id` or `/info`\n"
        "   - Send this command to get your own User ID.\n"
        "   - Reply to a message with this command to get that user's ID.\n"
        "   - Forward any message to me to get the original sender's ID.\n\n"
        "🔹 `/chatid`\n"
        "   - Get the ID of the current chat (group or private).\n\n"
        "🔗 **Share a Contact/Chat**\n"
        "   - Share a user, bot, group, or channel with me to instantly get its ID.\n\n"
        "📹 **Send me any video/photo/sticker**\n"
        "   - I'll reply with its `file_id` and other relevant info."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# --- CORRECTED id_handler ---
async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /id and /info, and intelligently extracts IDs from various contexts."""
    message = update.effective_message
    response_text = ""

    # Case 1: The message is a reply to another message.
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        response_text = f"👤 **User ID (from reply):** `{replied_user.id}`"
    
    # Case 2: The message is a forward.
    # Use message.forward_origin which is the modern and safe way to check.
    elif message.forward_origin:
        forward_info = message.forward_origin
        if forward_info.type == 'user':
            response_text = f"👤 **Forwarded User ID:** `{forward_info.sender_user.id}`"
        elif forward_info.type == 'hidden_user':
             response_text = f"👤 **Forwarded from a hidden user.**\n   - **Name:** {forward_info.sender_user_name}"
        elif forward_info.type == 'channel':
            response_text = (
                f"🌐 **Forwarded Channel Info**\n"
                f"   - **Title:** {forward_info.chat.title}\n"
                f"   - **Chat ID:** `{forward_info.chat.id}`"
            )
    
    # Case 3: It's just a simple command.
    else:
        user = update.effective_user
        response_text = f"👤 **Your User ID is:** `{user.id}`"

    await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

async def chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🌐 **This Chat's ID is:**\n`{chat_id}`", parse_mode=ParseMode.MARKDOWN)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TICKET_TYPE) -> None:
    contact = update.message.contact
    chat_id = contact.user_id 
    if contact.first_name and not contact.last_name:
        response_text = f"🌐 **Shared Chat ID:** `{chat_id}`"
    else:
        response_text = f"👤 **Shared User ID:** `{chat_id}`"
    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video = update.message.video
    response_text = f"✅ Video received!\n\n📹 **Video File ID:**\n`{video.file_id}`"
    if video.thumbnail:
        response_text += f"\n\n🖼️ **Thumbnail File ID:**\n`{video.thumbnail.file_id}`"
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sticker = update.message.sticker
    response_text = f"🎨 **Sticker File ID:**\n`{sticker.file_id}`"
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    file_id = update.message.photo[-1].file_id
    response_text = f"🖼️ **Photo File ID:**\n`{file_id}`"
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)


# --- Main Bot Logic with simplified handlers ---
def main() -> None:
    """Sets up and runs the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(("id", "info"), id_handler))
    application.add_handler(CommandHandler("chatid", chat_id_handler))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.VIDEO, video_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # NEW: A single, robust handler for all forwarded messages
    application.add_handler(MessageHandler(filters.FORWARDED, id_handler))
    
    port = int(os.environ.get('PORT', '10000'))
    logger.info(f"Starting bot on port {port}")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()