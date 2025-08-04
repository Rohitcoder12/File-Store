# bot.py

import logging
import os
from telegram import Update, Message
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


# --- NEW: Helper function to get the source of a forward ---
def get_forward_source_text(message: Message) -> str:
    """Checks if a message is forwarded and returns a formatted string with the source's info."""
    if not message.forward_origin:
        return ""  # Not a forward, return empty string

    origin = message.forward_origin
    source_text = ""

    if origin.type == 'user':
        sender = origin.sender_user
        source_text = f"👤 **Source:** {sender.full_name} (`{sender.id}`)"
    elif origin.type == 'hidden_user':
        source_text = f"👤 **Source:** {origin.sender_user_name} (ID Hidden by Privacy)"
    elif origin.type == 'channel':
        chat = origin.chat
        source_text = f"📢 **Source:** {chat.title} (`{chat.id}`)"
    
    return f"\n\n{source_text}" if source_text else ""


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
        "   - Reply to a message with this command to get that user's ID.\n\n"
        "🔹 `/chatid`\n"
        "   - Get the ID of the current chat (group or private).\n\n"
        "🔗 **Share a Contact/Chat**\n"
        "   - Share a user, bot, group, or channel with me to instantly get its ID.\n\n"
        "📹 **Send or Forward any Media**\n"
        "   - I'll reply with its `file_id` and the original source's ID if it's a forward."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /id. Now only processes replies and the user's own ID."""
    message = update.effective_message
    response_text = ""
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        response_text = f"👤 **User ID (from reply):** `{replied_user.id}`"
    else:
        user = update.effective_user
        response_text = f"👤 **Your User ID is:** `{user.id}`"
    await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

async def chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🌐 **This Chat's ID is:**\n`{chat_id}`", parse_mode=ParseMode.MARKDOWN)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.message.contact
    shared_id = contact.user_id 
    if contact.first_name and not contact.last_name:
        response_text = f"🌐 **Shared Chat/Channel ID:** `{shared_id}`"
    else:
        response_text = f"👤 **Shared User/Bot ID:** `{shared_id}`"
    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

# --- MODIFIED Media Handlers ---
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    video = message.video
    
    # Get media info
    response_text = f"📹 **Video File ID:**\n`{video.file_id}`"
    if video.thumbnail:
        response_text += f"\n\n🖼️ **Thumbnail File ID:**\n`{video.thumbnail.file_id}`"
    
    # Get forward info and add it to the response
    response_text += get_forward_source_text(message)
    
    await message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    
    # Get media info
    response_text = f"🖼️ **Photo File ID:**\n`{message.photo[-1].file_id}`"
    
    # Get forward info and add it to the response
    response_text += get_forward_source_text(message)
    
    await message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    
    # Get media info
    response_text = f"🎨 **Sticker File ID:**\n`{message.sticker.file_id}`"
    
    # Get forward info and add it to the response
    response_text += get_forward_source_text(message)

    await message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)


# --- Main Bot Logic (Simplified) ---
def main() -> None:
    """Sets up and runs the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(("id", "info"), id_handler))
    application.add_handler(CommandHandler("chatid", chat_id_handler))
    
    # Message handlers
    # These now handle both direct sends and forwards of their specific media type.
    application.add_handler(MessageHandler(filters.VIDEO, video_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # The general filters.FORWARDED handler is now removed to prevent double replies.
    
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