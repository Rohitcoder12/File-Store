import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters # NEW: Import MessageHandler and filters
from telegram.constants import ParseMode

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command.
    Greets the user and extracts their User ID and Profile Photo ID.
    """
    user = update.effective_user
    user_id = user.id
    
    logger.info(f"User {user.full_name} ({user_id}) started the bot.")
    
    message_text = (
        f"👋 Hello, {user.full_name}!\n\n"
        f"This bot can extract User IDs and Photo File IDs.\n\n"
        f"🔹 **Your Telegram User ID:**\n`{user_id}`\n\n"
    )
    
    try:
        photos = await user.get_profile_photos(limit=1)
        if photos and photos.photos:
            highest_res_photo = photos.photos[0][-1]
            photo_id = highest_res_photo.file_id
            
            message_text += (
                f"🖼️ **Your Current Profile Photo ID:**\n"
                f"`{photo_id}`\n\n"
            )
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

# NEW: Handler for photos
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles incoming photos and sends back their file_id.
    """
    user = update.effective_user
    logger.info(f"User {user.full_name} ({user.id}) sent a photo.")
    
    # When you send a photo, Telegram provides it in several resolutions.
    # The `update.message.photo` is a list of these resolutions.
    # The last one in the list (`-1`) is always the highest quality.
    highest_res_photo = update.message.photo[-1]
    file_id = highest_res_photo.file_id
    
    # You can also get other info like width, height, and file size
    width = highest_res_photo.width
    height = highest_res_photo.height
    file_size_kb = round(highest_res_photo.file_size / 1024, 1) if highest_res_photo.file_size else 'N/A'

    response_text = (
        f"✅ Photo received!\n\n"
        f"🖼️ **File ID (Highest Res):**\n`{file_id}`\n\n"
        f"📐 **Dimensions:** {width}x{height} pixels\n"
        f"💾 **File Size:** ~{file_size_kb} KB"
    )
    
    # Reply directly to the photo the user sent
    await update.message.reply_text(
        text=response_text,
        parse_mode=ParseMode.MARKDOWN
    )


# --- Main Bot Logic ---

def main() -> None:
    """Sets up and runs the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    # NEW: Register the photo handler. It will trigger for any message that is a photo.
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    port = int(os.environ.get('PORT', '8443'))
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()