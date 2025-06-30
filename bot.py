import logging
import os
import base64
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.constants import ParseMode
from telegram.error import BadRequest

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# PORT is provided by Render
PORT = int(os.environ.get('PORT', '8443'))

# Get the webhook URL from an environment variable. Render will provide this.
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
DATABASE_CHANNEL_ID = os.environ.get("DATABASE_CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")
if not WEBHOOK_URL:
    raise ValueError("No WEBHOOK_URL found in environment variables")
if not DATABASE_CHANNEL_ID:
    raise ValueError("No DATABASE_CHANNEL_ID found in environment variables")


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Bot Handlers (v13.x Syntax) ---

def start_handler(update: Update, context: CallbackContext) -> None:
    """Handles the /start command, including deep linking."""
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) started the bot.")
    
    if context.args:
        try:
            encoded_payload = context.args[0]
            decoded_payload_bytes = base64.urlsafe_b64decode(encoded_payload)
            payload_str = decoded_payload_bytes.decode('utf-8')
            file_type, file_id = payload_str.split(':', 1)
            
            logger.info(f"User {user.id} requested file. Type: {file_type}, ID: {file_id}")
            update.message.reply_text("✅ Your file is on its way...")

            if file_type == 'photo':
                context.bot.send_photo(chat_id=user.id, photo=file_id)
            elif file_type == 'video':
                context.bot.send_video(chat_id=user.id, video=file_id)
            elif file_type == 'document':
                context.bot.send_document(chat_id=user.id, document=file_id)
            elif file_type == 'audio':
                context.bot.send_audio(chat_id=user.id, audio=file_id)
            else:
                update.message.reply_text("❌ Sorry, this file type is not supported.")

        except (BadRequest, ValueError, IndexError) as e:
            logger.error(f"Error processing deep link: {e}")
            update.message.reply_text("❌ Sorry, the link is invalid or has expired.")
    else:
        show_welcome_message(update, context)

def show_welcome_message(update: Update, context: CallbackContext) -> None:
    """Sends the standard welcome/help message."""
    user_id = update.effective_user.id
    credit_line = "Made with ❤️ by [RexonBlack](https://t.me/RexonBlack)"

    message_text = (
        f"👋 Hello, {update.effective_user.full_name}!\n\n"
        f"**This bot has two main functions:**\n\n"
        f"1️⃣ **ID Extractor**\n"
        f"   - Your User ID is: `{user_id}`\n\n"
        f"2️⃣ **File Sharer**\n"
        f"   - Send me any file and I'll give you a permanent, shareable link.\n\n"
        f"——\n{credit_line}"
    )
    update.message.reply_text(
        text=message_text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

def file_handler(update: Update, context: CallbackContext) -> None:
    """Handles incoming files, extracts info, and generates a shareable link."""
    user = update.effective_user
    message = update.message
    file_type = None
    file_id = None

    if message.photo:
        file_type = 'photo'
        file_id = message.photo[-1].file_id
    elif message.video:
        file_type = 'video'
        file_id = message.video.file_id
    elif message.audio:
        file_type = 'audio'
        file_id = message.audio.file_id
    elif message.document:
        file_type = 'document'
        file_id = message.document.file_id
    
    if file_type and file_id:
        logger.info(f"Received {file_type} from user {user.full_name} ({user.id}).")
        
        try:
            message.forward(chat_id=DATABASE_CHANNEL_ID)
        except Exception as e:
            logger.warning(f"Could not forward file to database channel: {e}")

        payload_str = f"{file_type}:{file_id}"
        encoded_payload = base64.urlsafe_b64encode(payload_str.encode('utf-8')).decode('utf-8')
        
        bot_username = context.bot.username
        share_link = f"https://t.me/{bot_username}?start={encoded_payload}"
        
        message.reply_text(
            "✅ File saved! Here is your shareable link:\n\n"
            f"`{share_link}`",
            parse_mode=ParseMode.MARKDOWN
        )

# --- Main Bot Logic ---
def main() -> None:
    """Sets up and runs the bot."""
    # Using the old Updater class
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start_handler))
    dispatcher.add_handler(CommandHandler("help", show_welcome_message))
    
    # Using the old Filters class
    dispatcher.add_handler(MessageHandler(Filters.photo, file_handler))
    dispatcher.add_handler(MessageHandler(Filters.video, file_handler))
    dispatcher.add_handler(MessageHandler(Filters.audio, file_handler))
    dispatcher.add_handler(MessageHandler(Filters.document, file_handler))
    
    # Using the old start_webhook method
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
    
    updater.idle()

if __name__ == "__main__":
    main()