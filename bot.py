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


# --- NEW: A Universal Handler for ALL Forwarded Messages ---
async def universal_forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles any forwarded message, extracts media and source IDs."""
    message = update.effective_message
    response_text = ""
    
    # --- Part 1: Extract Media ID if it exists ---
    if message.photo:
        response_text += f"🖼️ **Photo File ID:**\n`{message.photo[-1].file_id}`\n\n"
    elif message.video:
        response_text += f"📹 **Video File ID:**\n`{message.video.file_id}`\n\n"
        if message.video.thumbnail:
            response_text += f"🖼️ **Thumbnail File ID:**\n`{message.video.thumbnail.file_id}`\n\n"
    elif message.sticker:
        response_text += f"🎨 **Sticker File ID:**\n`{message.sticker.file_id}`\n\n"
    # Note: You can add more media types here like audio or document if needed.

    # --- Part 2: Extract the Source ID ---
    origin = message.forward_origin
    source_text = ""
    if origin.type == 'user':
        sender = origin.sender_user
        source_text = f"👤 **Source:** {sender.full_name} (`{sender.id}`)"
    elif origin.type == 'hidden_user':
        source_text = f"👤 **Source:** {origin.sender_user_name} (ID Hidden)"
    elif origin.type == 'channel':
        chat = origin.chat
        source_text = f"📢 **Source:** {chat.title} (`{chat.id}`)"

    response_text += source_text

    # --- Part 3: Send the combined response ---
    if response_text:
        await message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)


# --- Standard Handlers (Now Simplified) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"👋 Hello, {update.effective_user.full_name}!\n\nI am Id Extractor Bot. Forward any message or send me any media to get its ID.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = "ℹ️ **How to use me:**\n\n• **Forward any message:** I will give you the original sender's ID (user, bot, or channel).\n\n• **Send me any media:** I will give you the File ID for any photo, video, or sticker.\n\n• **/id:** Get your own User ID.\n\n• **/chatid:** Get the current chat's ID."
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"👤 **Your User ID is:** `{update.effective_user.id}`", parse_mode=ParseMode.MARKDOWN)

async def chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"🌐 **This Chat's ID is:** `{update.effective_chat.id}`", parse_mode=ParseMode.MARKDOWN)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.message.contact
    await update.message.reply_text(f"👤 **Shared User/Bot ID:** `{contact.user_id}`", parse_mode=ParseMode.MARKDOWN)

# These handlers now only work for DIRECTLY sent media
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response_text = f"📹 **Video File ID:**\n`{update.message.video.file_id}`"
    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response_text = f"🖼️ **Photo File ID:**\n`{update.message.photo[-1].file_id}`"
    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response_text = f"🎨 **Sticker File ID:**\n`{update.message.sticker.file_id}`"
    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)


# --- Main Bot Logic ---
def main() -> None:
    """Sets up and runs the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(("id", "info"), id_handler))
    application.add_handler(CommandHandler("chatid", chat_id_handler))
    
    # NEW: The single, powerful handler for ALL forwarded messages
    application.add_handler(MessageHandler(filters.FORWARDED, universal_forward_handler))

    # Handlers for DIRECTLY SENT messages
    application.add_handler(MessageHandler(filters.VIDEO, video_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    
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