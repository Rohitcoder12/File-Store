import logging
import os
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import BadRequest

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
DATABASE_CHANNEL_ID = os.environ.get("DATABASE_CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")
if not DATABASE_CHANNEL_ID:
    raise ValueError("No DATABASE_CHANNEL_ID found in environment variables")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Bot Handlers ---

# UPDATED: start_handler now decodes file_type and file_id to send a new message
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command, including deep linking for sending files."""
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) started the bot.")
    
    if context.args:
        try:
            # Decode the payload from the deep link
            encoded_payload = context.args[0]
            decoded_payload_bytes = base64.urlsafe_b64decode(encoded_payload)
            payload_str = decoded_payload_bytes.decode('utf-8')
            
            # Split the payload into file_type and file_id
            file_type, file_id = payload_str.split(':', 1)
            
            logger.info(f"User {user.id} requested file. Type: {file_type}, ID: {file_id}")
            
            await update.message.reply_text("✅ Your file is on its way...")

            # Use the correct method to send the file based on its type
            if file_type == 'photo':
                await context.bot.send_photo(chat_id=user.id, photo=file_id)
            elif file_type == 'video':
                await context.bot.send_video(chat_id=user.id, video=file_id)
            elif file_type == 'document':
                await context.bot.send_document(chat_id=user.id, document=file_id)
            elif file_type == 'audio':
                await context.bot.send_audio(chat_id=user.id, audio=file_id)
            else:
                await update.message.reply_text("❌ Sorry, this file type is not supported.")

        except (BadRequest, ValueError, IndexError) as e:
            logger.error(f"Error processing deep link: {e}")
            await update.message.reply_text("❌ Sorry, the link is invalid or has expired.")
        except Exception as e:
            logger.error(f"Unexpected deep link error for user {user.id}: {e}")
            await update.message.reply_text("❌ An unexpected error occurred.")
    else:
        # Regular /start command without a payload
        await show_welcome_message(update, context)

# A dedicated function for the welcome/help message
async def show_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the standard welcome/help message."""
    user_id = update.effective_user.id
    credit_line = "Made with ❤️ by [RexonBlack](https://t.me/RexonBlack)"

    message_text = (
        f"👋 Hello, {update.effective_user.full_name}!\n\n"
        f"**This bot has two main functions:**\n\n"
        f"1️⃣ **ID Extractor**\n"
        f"   - Your User ID is: `{user_id}`\n\n"
        f"2️⃣ **File Sharer**\n"
        f"   - Send me any file (photo, video, document) and I'll give you a permanent, shareable link.\n\n"
        f"——\n{credit_line}"
    )
    await update.message.reply_text(
        text=message_text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )
    
# UPDATED: file_handler now extracts file_id and file_type to create the link
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming files, extracts info, and generates a shareable link."""
    user = update.effective_user
    message = update.message
    file_type = None
    file_id = None

    # Determine file type and get the file_id
    if message.photo:
        file_type = 'photo'
        file_id = message.photo[-1].file_id  # Highest resolution
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
        
        # Forward to database for backup (optional but good practice)
        try:
            await message.forward(chat_id=DATABASE_CHANNEL_ID)
        except Exception as e:
            logger.warning(f"Could not forward file to database channel: {e}")

        # Create the payload string: "file_type:file_id"
        payload_str = f"{file_type}:{file_id}"
        # URL-safe base64 encoding
        encoded_payload = base64.urlsafe_b64encode(payload_str.encode('utf-8')).decode('utf-8')
        
        bot_username = (await context.bot.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={encoded_payload}"
        
        await message.reply_text(
            "✅ File saved! Here is your shareable link:\n\n"
            f"`{share_link}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply_text("❌ I could not process this file type.")

# --- Main Bot Logic ---
def main() -> None:
    """Sets up and runs the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", show_welcome_message))
    
    # Register a separate handler for each file type
    application.add_handler(MessageHandler(filters.PHOTO, file_handler))
    application.add_handler(MessageHandler(filters.VIDEO, file_handler))
    application.add_handler(MessageHandler(filters.AUDIO, file_handler))
    application.add_handler(MessageHandler(filters.Document, file_handler))
    
    port = int(os.environ.get('PORT', '8443'))
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()