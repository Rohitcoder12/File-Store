# bot.py

import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("No WEBHOOK_URL found in environment variables")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and shows a welcome message."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello, {user.full_name}!\n\n"
        "I am the Id Extractor Bot. I can get User, Chat, Photo, and Sticker IDs for you.\n\n"
        "Type /help to see everything I can do!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a detailed help message."""
    help_text = (
        "ℹ️ **Here's what I can do:**\n\n"
        "🔹 `/id` or `/info`\n"
        "   - Send this command to get your own User ID.\n"
        "   - Reply to a message with this command to get that user's ID.\n"
        "   - Forward any message to me to get the original sender's ID and the chat's ID (if from a channel/group).\n\n"
        "🔹 `/chatid`\n"
        "   - Get the ID of the current chat (group or private).\n\n"
        "📷 **Send me any photo**\n"
        "   I'll reply with its `file_id` and other details.\n\n"
        "🎨 **Send me any sticker**\n"
        "   I'll reply with its `file_id` and `file_unique_id`."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /id and /info, and intelligently extracts IDs from various contexts."""
    message = update.effective_message
    response_text = ""

    # Case 1: Replying to a message
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        response_text = (
            f"👤 **User Info (from reply)**\n"
            f"   - **Name:** {replied_user.full_name}\n"
            f"   - **User ID:** `{replied_user.id}`\n"
        )
        if replied_user.username:
            response_text += f"   - **Username:** @{replied_user.username}\n"

    # Case 2: Forwarded message
    elif message.forward_from or message.forward_from_chat:
        # If forwarded from a user
        if message.forward_from:
            fwd_user = message.forward_from
            response_text = (
                f"👤 **User Info (from forward)**\n"
                f"   - **Name:** {fwd_user.full_name}\n"
                f"   - **User ID:** `{fwd_user.id}`\n"
            )
        # If forwarded from a channel/group
        if message.forward_from_chat:
            fwd_chat = message.forward_from_chat
            response_text += (
                f"\n🌐 **Chat Info (from forward)**\n"
                f"   - **Title:** {fwd_chat.title}\n"
                f"   - **Chat ID:** `{fwd_chat.id}`\n"
                f"   - **Type:** {fwd_chat.type.capitalize()}\n"
            )

    # Case 3: Just the /id command sent by a user
    else:
        user = update.effective_user
        response_text = f"👤 **Your User ID is:** `{user.id}`"

    await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

async def chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the current chat's ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🌐 **This Chat's ID is:**\n`{chat_id}`", parse_mode=ParseMode.MARKDOWN)

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming stickers and sends back their file_id."""
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) sent a sticker.")

    sticker = update.message.sticker
    response_text = (
        f"✅ Sticker received!\n\n"
        f"🎨 **File ID:**\n`{sticker.file_id}`\n\n"
        f"🔖 **File Unique ID:**\n`{sticker.file_unique_id}`"
    )
    if sticker.set_name:
        response_text += f"\n\n✨ **Set Name:** `{sticker.set_name}`"
    
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming photos and sends back their file_id."""
    # This function remains the same as your original
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) sent a photo.")
    highest_res_photo = update.message.photo[-1]
    file_id = highest_res_photo.file_id
    width = highest_res_photo.width
    height = highest_res_photo.height
    file_size_kb = round(highest_res_photo.file_size / 1024, 1) if highest_res_photo.file_size else 'N/A'

    response_text = (
        f"✅ Photo received!\n\n"
        f"🖼️ **File ID (Highest Res):**\n`{file_id}`\n\n"
        f"📐 **Dimensions:** {width}x{height} pixels\n"
        f"💾 **File Size:** ~{file_size_kb} KB"
    )
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)


# --- Main Bot Logic ---

def main() -> None:
    """Sets up and runs the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(("id", "info"), id_handler)) # Handles /id and /info
    application.add_handler(CommandHandler("chatid", chat_id_handler))
    
    # Register message handlers
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    # This handler is a catch-all for forwarded messages that aren't commands
    application.add_handler(MessageHandler(filters.FORWARDED, id_handler))
    
    port = int(os.environ.get('PORT', '8443'))
    
    logger.info(f"Starting bot on port {port}")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()