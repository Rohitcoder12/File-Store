import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")
if not WEBHOOK_URL:
    raise ValueError("No WEBHOOK_URL found in environment variables")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# --- Command Handlers ---

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command. Extracts User ID and Profile Photo ID."""
    user = update.effective_user
    user_id = user.id
    
    logger.info(f"User {user.full_name} ({user.id}) started the bot.")
    
    # Build the response message
    message_text = (
        f"👋 Hello, {user.full_name}!\n\n"
        f"🔹 **Your Telegram User ID:**\n`{user_id}`\n\n"
    )
    
    # Get Profile Photo ID
    try:
        photos = await user.get_profile_photos(limit=1)
        if photos and photos.photos:
            highest_res_photo = photos.photos[0][-1]
            photo_id = highest_res_photo.file_id
            message_text += f"🖼️ **Your Profile Photo ID:**\n`{photo_id}`\n\n"
        else:
            message_text += "🖼️ You do not have a profile picture set.\n\n"
    except Exception as e:
        logger.error(f"Could not fetch profile photo for user {user_id}: {e}")
        message_text += "🖼️ Could not retrieve profile picture information.\n\n"

    message_text += "➡️ **To get a photo's File ID, just send me the photo!**"

    await update.message.reply_text(
        text=message_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming photos and sends back their file_id."""
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) sent a photo.")
    
    highest_res_photo = update.message.photo[-1]
    file_id = highest_res_photo.file_id

    response_text = (
        f"✅ Photo received!\n\n"
        f"🖼️ **File ID (Highest Res):**\n`{file_id}`"
    )
    
    await update.message.reply_text(
        text=response_text,
        parse_mode=ParseMode.MARKDOWN
    )

# --- Main Bot Logic ---
def main() -> None:
    """Sets up and runs the bot for Render."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    port = int(os.environ.get('PORT', '8443'))
    
    # Start the webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()