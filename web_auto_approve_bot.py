# File: web_auto_approve_bot.py

import os
import logging
import asyncio
import threading

# --- Web Server Imports ---
from flask import Flask

# --- Pyrogram Imports ---
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Loader ---
class Config:
    try:
        API_ID = int(os.environ.get("API_ID"))
        API_HASH = os.environ.get("API_HASH")
        BOT_TOKEN = os.environ.get("BOT_TOKEN")
        ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))
        ALLOWED_CHANNELS_STR = os.environ.get("ALLOWED_CHANNELS", "")
        ALLOWED_CHANNELS = [int(ch_id) for ch_id in ALLOWED_CHANNELS_STR.split()]
        LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL")) if os.environ.get("LOG_CHANNEL") else None
    except (ValueError, TypeError) as e:
        logger.critical(f"One of the required environment variables is missing or invalid: {e}")
        exit(1)

# --- Flask Web App for Health Checks ---
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    """Endpoint for Render's health checks."""
    return "Bot is alive and running!", 200

# --- Pyrogram Client Setup ---
app = Client(
    "AutoApproveBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# --- Command Handlers ---
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text(
        "👋 Hello! I am an auto-approve bot.\n\n"
        "I will automatically accept join requests for the channels I am configured to monitor.\n"
        "Make sure I am an admin in your channel with the 'Invite Users' permission."
    )

@app.on_message(filters.command("ping") & filters.user(Config.ADMIN_USER_ID))
async def ping_command(client, message):
    await message.reply_text("✅ Pong! I am alive and running.")

# --- The Core Logic: Join Request Handler ---
@app.on_chat_join_request()
async def handle_join_request(client: Client, request: ChatJoinRequest):
    chat_id = request.chat.id
    user_id = request.from_user.id
    user_name = request.from_user.first_name

    if chat_id not in Config.ALLOWED_CHANNELS:
        logger.warning(f"Received join request for unauthorized channel {chat_id}. Ignoring.")
        return

    try:
        logger.info(f"Approving join request for {user_name} in channel {request.chat.title} ({chat_id}).")
        await client.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        
        if Config.LOG_CHANNEL:
            log_message = (
                f"✅ **Join Request Approved**\n\n"
                f"**Channel:** {request.chat.title} (`{chat_id}`)\n"
                f"**User:** [{user_name}](tg://user?id={user_id})\n"
                f"**User ID:** `{user_id}`"
            )
            await client.send_message(Config.LOG_CHANNEL, log_message)
    except Exception as e:
        logger.error(f"Failed to approve join request for {user_id} in {chat_id}: {e}")
        if Config.LOG_CHANNEL:
            await client.send_message(Config.LOG_CHANNEL, f"❌ **Error:** Failed to approve join request.\n`{e}`")

# --- Function to run the Pyrogram bot ---
async def run_bot_async():
    logger.info("Starting Pyrogram bot client...")
    await app.start()
    logger.info("Bot has started successfully.")
    # Keep the bot running indefinitely
    await asyncio.Event().wait()

def start_bot_thread():
    """Runs the bot in a new asyncio event loop on a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

# --- Main Execution ---
if __name__ == "__main__":
    if not Config.ALLOWED_CHANNELS:
        logger.warning("No ALLOWED_CHANNELS configured. The bot will not approve any requests.")

    # Start the bot in a separate daemon thread
    # A daemon thread will exit when the main program exits
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()

    # Run the Flask web server in the main thread
    # Render provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask web server on port {port}...")
    web_app.run(host='0.0.0.0', port=port)
