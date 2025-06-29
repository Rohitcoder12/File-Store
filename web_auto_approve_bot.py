# File: web_bot.py

import os
import asyncio
import sqlite3
import logging
import string
import random
import threading
from datetime import datetime

# --- Web Server Imports ---
from flask import Flask

# --- Pyrogram Imports ---
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
)
from pyrogram.errors import UserNotParticipant, QueryIdInvalid

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Loader ---
class Config:
    try:
        API_ID = int(os.environ.get("API_ID"))
        API_HASH = os.environ.get("API_HASH")
        BOT_TOKEN = os.environ.get("BOT_TOKEN")
        ADMINS = [int(admin) for admin in os.environ.get("ADMINS", "").split()]
        DB_CHANNEL = int(os.environ.get("DB_CHANNEL"))
        LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", None))
        FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", None)
        START_MESSAGE = os.environ.get("START_MESSAGE", 
            "**👋 Hello {mention}!**\n\n"
            "I am a powerful File Sharing Bot. I can store your files and give you a permanent shareable link.\n\n"
            "**Features:**\n"
            "✅ Send any file to get a link.\n"
            "✅ Use `/batch` to combine multiple files into one link.\n"
            "✅ Use `/myfiles` to manage your uploaded files.\n\n"
            "**Made with ❤️**"
        )
    except (ValueError, TypeError) as e:
        logger.critical(f"One of the required environment variables is missing or invalid: {e}")
        exit(1)

# --- State Management for Batch Uploads ---
user_batch_mode = {}

# --- Database Setup (SQLite) ---
DB_FILE = "bot_database.db"

def init_db():
    # ... (Database functions are exactly the same as before) ...
    # ... I am omitting them here for brevity, but they should be in your file.
    conn = sqlite3.connect(DB_FILE, check_same_thread=False) # Important: Add check_same_thread=False for threading
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, join_date TEXT )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY, user_id INTEGER, db_message_id INTEGER, file_name TEXT, 
            file_type TEXT, file_size INTEGER, upload_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def db_connect():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def add_user(user_id):
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", (user_id, datetime.now().isoformat()))
        conn.commit()

def generate_file_id(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def save_file(user_id, db_message_id, file_name, file_type, file_size):
    file_id = generate_file_id()
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO files (file_id, user_id, db_message_id, file_name, file_type, file_size, upload_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_id, user_id, db_message_id, file_name, file_type, file_size, datetime.now().isoformat()))
        conn.commit()
    return file_id

def get_file_details(file_id):
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT db_message_id FROM files WHERE file_id=?", (file_id,))
        result = cursor.fetchone()
    return result[0] if result else None

# ... (Include all other database helper functions here: get_user_files, count_user_files, etc.) ...
def get_user_files(user_id, offset=0, limit=10):
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_name, file_size FROM files WHERE user_id=? ORDER BY upload_date DESC LIMIT ? OFFSET ?", (user_id, limit, offset))
        files = cursor.fetchall()
    return files

def count_user_files(user_id):
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE user_id=?", (user_id,))
        count = cursor.fetchone()[0]
    return count

def delete_file_db(file_id):
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE file_id=?", (file_id,))
        conn.commit()

def get_stats():
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM files")
        total_files = cursor.fetchone()[0]
    return total_users, total_files

def get_all_user_ids():
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
    return user_ids

# --- Flask Web App for Health Checks ---
web_app = Flask(__name__)
@web_app.route('/')
def health_check():
    return "Bot is alive and running!", 200

# --- Pyrogram Client Setup ---
app = Client("FileShareBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

# ... (All your @app.on_message and @app.on_callback_query handlers go here) ...
# ... They are exactly the same as before. I am omitting them for brevity. ...
# --- Start of Bot Handlers ---
async def check_subscription(client, message):
    if not Config.FORCE_SUB_CHANNEL: return True
    try:
        await client.get_chat_member(Config.FORCE_SUB_CHANNEL, message.from_user.id)
    except UserNotParticipant:
        join_url = f"https://t.me/{Config.FORCE_SUB_CHANNEL}"
        await message.reply_text(f"**You must join our channel to use this bot!**\n\nPlease join 👉 [{Config.FORCE_SUB_CHANNEL}]({join_url})", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=join_url)]]))
        return False
    return True

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    # ... (same as before) ...
    add_user(message.from_user.id)
    if not await check_subscription(client, message): return
    if len(message.command) > 1 and message.command[1].startswith("get_"):
        file_id = message.command[1].split("_", 1)[1]
        db_message_id = get_file_details(file_id)
        if db_message_id: await client.copy_message(message.from_user.id, Config.DB_CHANNEL, db_message_id)
        else: await message.reply("File not found.")
        return
    await message.reply_text(Config.START_MESSAGE.format(mention=message.from_user.mention))

# (ADD ALL OTHER BOT HANDLERS - file_handler, my_files, stats, etc.)

# --- End of Bot Handlers ---

def _format_bytes(size_bytes):
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(size_bytes.bit_length() / 10)
    return f"{round(size_bytes / (1024 ** i), 2)} {size_name[i]}"

# --- Main Execution ---
def run_bot():
    logger.info("Starting Pyrogram bot client...")
    app.run()

if __name__ == "__main__":
    init_db()
    
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Run the Flask web server in the main thread
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask web server on port {port}...")
    web_app.run(host='0.0.0.0', port=port)
