# bot.py

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# NEW: Import PicklePersistence
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    PicklePersistence
)
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


# --- Handlers (Unchanged) ---
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
        "📹 **Send me any video**\n"
        "   - I'll reply with its `file_id` and a button to extract the thumbnail.\n\n"
        "📷 **Send me any photo**\n"
        "   - I'll reply with its `file_id` and other details.\n\n"
        "🎨 **Send me any sticker**\n"
        "   - I'll reply with its `file_id`."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    response_text = ""
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        response_text = f"👤 **User ID (from reply):** `{replied_user.id}`"
    elif message.forward_from or message.forward_from_chat:
        if message.forward_from:
            fwd_user = message.forward_from
            response_text = f"👤 **Forwarded User ID:** `{fwd_user.id}`"
        if message.forward_from_chat:
            fwd_chat = message.forward_from_chat
            response_text += f"\n🌐 **Forwarded Chat ID:** `{fwd_chat.id}`"
    else:
        user = update.effective_user
        response_text = f"👤 **Your User ID is:** `{user.id}`"
    await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

async def chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🌐 **This Chat's ID is:**\n`{chat_id}`", parse_mode=ParseMode.MARKDOWN)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.message.contact
    chat_id = contact.user_id 
    if contact.first_name and not contact.last_name:
        response_text = f"🌐 **Shared Chat ID:** `{chat_id}`"
    else:
        response_text = f"👤 **Shared User ID:** `{chat_id}`"
    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

# --- The logic for these two handlers is now reliable thanks to persistence ---
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video = update.message.video
    response_text = f"✅ Video received!\n\n📹 **Video File ID:**\n`{video.file_id}`"
    
    reply_markup = None
    if video.thumbnail:
        # We send the message and get its ID to use as a key
        sent_message = await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)
        message_id = sent_message.message_id
        
        # Store the thumbnail_id in persistent chat_data
        context.chat_data[message_id] = video.thumbnail.file_id
        
        button = InlineKeyboardButton("Extract Thumbnail 🖼️", callback_data=f"get_thumb:{message_id}")
        reply_markup = InlineKeyboardMarkup([[button]])

        # Edit the message to add the button
        await sent_message.edit_reply_markup(reply_markup=reply_markup)
    else:
        # If no thumbnail, just send the text
        await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("get_thumb:"):
        message_id = int(data.split(":", 1)[1])
        # Retrieve the thumbnail_id from our persistent storage
        thumbnail_id = context.chat_data.pop(message_id, None)

        if thumbnail_id:
            caption = f"✅ Here is the thumbnail.\n\n**File ID:**\n`{thumbnail_id}`"
            await query.message.reply_photo(photo=thumbnail_id, caption=caption, parse_mode=ParseMode.MARKDOWN)
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.edit_message_text(text="This button has expired or the bot was recently updated. Please send the video again.")

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sticker = update.message.sticker
    response_text = f"🎨 **Sticker File ID:**\n`{sticker.file_id}`"
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    file_id = update.message.photo[-1].file_id
    response_text = f"🖼️ **Photo File ID:**\n`{file_id}`"
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)

# --- Main Bot Logic with Persistence ---
def main() -> None:
    """Sets up and runs the bot with persistence."""
    # NEW: Create a persistence object
    # This will create a file named "bot_persistence" in your project directory
    persistence = PicklePersistence(filepath="bot_persistence")

    # NEW: Add the persistence object to the Application Builder
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .build()
    )
    
    # Register all handlers (unchanged)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(("id", "info"), id_handler))
    application.add_handler(CommandHandler("chatid", chat_id_handler))
    
    application.add_handler(MessageHandler(filters.VIDEO, video_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    application.add_handler(MessageHandler(filters.FORWARDED, id_handler))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    application.add_handler(CallbackQueryHandler(button_callback_handler))
    
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