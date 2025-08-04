# bot.py

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
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
        "I am an advanced Id Extractor Bot.\n\n"
        "Type /help to see everything I can do!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a detailed help message."""
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
    """Handles /id and /info, and intelligently extracts IDs from various contexts."""
    # This logic remains the same
    message = update.effective_message
    response_text = ""
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        response_text = (
            f"👤 **User Info (from reply)**\n"
            f"   - **Name:** {replied_user.full_name}\n"
            f"   - **User ID:** `{replied_user.id}`\n"
        )
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
    """Sends the current chat's ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🌐 **This Chat's ID is:**\n`{chat_id}`", parse_mode=ParseMode.MARKDOWN)

# --- NEW: Handler for Shared Contacts/Chats ---
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles shared contacts, which can be users, bots, groups or channels."""
    contact = update.message.contact
    user_id = contact.user_id
    chat_id = contact.user_id # For chats/channels, user_id is the chat_id
    
    # Telegram sends different info for shared users vs shared chats
    if contact.first_name and not contact.last_name: # Likely a channel or group
        response_text = f"🌐 **Shared Chat Info**\n   - **Title:** {contact.first_name}\n   - **Chat ID:** `{chat_id}`"
    else: # It's a user or bot
        full_name = f"{contact.first_name} {contact.last_name or ''}".strip()
        response_text = f"👤 **Shared User Info**\n   - **Name:** {full_name}\n   - **User ID:** `{user_id}`"

    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)


# --- MODIFIED: Video Handler now with Button ---
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming videos and sends back their file_id and a thumbnail button."""
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) sent a video.")

    video = update.message.video
    response_text = (
        f"✅ Video received!\n\n"
        f"📹 **Video File ID:**\n`{video.file_id}`\n\n"
        f"⏱️ **Duration:** {video.duration} seconds\n"
        f"📐 **Dimensions:** {video.width}x{video.height}\n"
    )

    reply_markup = None
    if video.thumbnail:
        thumbnail_file_id = video.thumbnail.file_id
        # We pass the thumbnail's file_id in the callback_data
        button = InlineKeyboardButton("Extract Thumbnail 🖼️", callback_data=f"get_thumb:{thumbnail_file_id}")
        reply_markup = InlineKeyboardMarkup([[button]])

    await update.message.reply_text(
        text=response_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# --- NEW: Handler for Button Clicks ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callback queries from inline buttons."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press

    data = query.data
    if data.startswith("get_thumb:"):
        thumbnail_id = data.split(":", 1)[1]
        caption = f"✅ Here is the thumbnail.\n\n**File ID:**\n`{thumbnail_id}`"
        
        # Send the thumbnail as a photo
        await query.message.reply_photo(
            photo=thumbnail_id,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
        # Optional: Edit the original message to remove the button after it's clicked
        await query.edit_message_reply_markup(reply_markup=None)

# --- Other Media Handlers (Unchanged) ---
async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    highest_res_photo = update.message.photo[-1]
    file_id = highest_res_photo.file_id
    response_text = (
        f"✅ Photo received!\n\n"
        f"🖼️ **File ID (Highest Res):**\n`{file_id}`"
    )
    await update.message.reply_text(text=response_text, parse_mode=ParseMode.MARKDOWN)


# --- Main Bot Logic ---
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
    application.add_handler(MessageHandler(filters.FORWARDED, id_handler))
    # NEW: Handler for shared contacts/chats
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # NEW: Handler for button callbacks
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    
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