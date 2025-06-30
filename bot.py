import logging
import os
import base64 # For encoding the links
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import BadRequest # To handle errors gracefully

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
# Get the Database Channel ID from environment variables
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

# The start function now handles deep linking for file sharing
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command, including deep linking."""
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) started the bot.")
    
    # Check if the command has a payload (from a deep link)
    if context.args:
        try:
            # The payload is the encoded message_id
            encoded_id = context.args[0]
            # Decode the base64 string to get the original message_id
            decoded_id_bytes = base64.b64decode(encoded_id)
            message_id_to_forward = int(decoded_id_bytes.decode('utf-8'))
            
            logger.info(f"User {user.id} requested file with message_id: {message_id_to_forward}")
            
            await update.message.reply_text("✅ Your file is on its way...")
            
            # Forward the message from the database channel to the user
            await context.bot.forward_message(
                chat_id=user.id,
                from_chat_id=DATABASE_CHANNEL_ID,
                message_id=message_id_to_forward
            )
        except BadRequest as e:
            logger.error(f"Error forwarding file: {e}")
            await update.message.reply_text("❌ Sorry, the link is invalid or the file was deleted.")
        except Exception as e:
            logger.error(f"Deep link processing error for user {user.id}: {e}")
            await update.message.reply_text("❌ An unexpected error occurred. The link may be broken.")
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
    
# A universal handler for all file types
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming files, forwards them, and generates a shareable link."""
    user = update.effective_user
    logger.info(f"Received a file from user {user.full_name} ({user.id}).")

    try:
        # Forward the message to the database channel
        forwarded_message = await update.message.forward(chat_id=DATABASE_CHANNEL_ID)
        
        # Get the message_id of the file in the database channel
        file_message_id = forwarded_message.message_id
        
        # Encode the message_id using base64 for a cleaner URL
        id_bytes = str(file_message_id).encode('utf-8')
        encoded_id = base64.b64encode(id_bytes).decode('utf-8')
        
        # Get the bot's username to create the link
        bot_username = (await context.bot.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={encoded_id}"
        
        await update.message.reply_text(
            "✅ File saved! Here is your shareable link:\n\n"
            f"`{share_link}`",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Could not handle/forward file for user {user.id}: {e}")
        await update.message.reply_text("❌ Sorry, I was unable to process your file. Please try again.")

# --- Main Bot Logic ---
def main() -> None:
    """Sets up and runs the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", show_welcome_message))
    
    # A single handler for all supported file types
    # THIS IS THE CORRECTED LINE:
    file_filters = filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document
    application.add_handler(MessageHandler(file_filters, file_handler))
    
    port = int(os.environ.get('PORT', '8443'))
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()