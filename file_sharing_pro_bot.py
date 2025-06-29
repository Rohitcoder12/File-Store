import os
import asyncio
import sqlite3
import logging
import string
import random
from datetime import datetime

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
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            user_id INTEGER,
            db_message_id INTEGER,
            file_name TEXT,
            file_type TEXT,
            file_size INTEGER,
            upload_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

# --- Database Helper Functions ---
def add_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", (user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def generate_file_id(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def save_file(user_id, db_message_id, file_name, file_type, file_size):
    file_id = generate_file_id()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO files (file_id, user_id, db_message_id, file_name, file_type, file_size, upload_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (file_id, user_id, db_message_id, file_name, file_type, file_size, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return file_id

def get_file_details(file_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT db_message_id FROM files WHERE file_id=?", (file_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_files(user_id, offset=0, limit=10):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT file_id, file_name, file_size FROM files
        WHERE user_id=? ORDER BY upload_date DESC LIMIT ? OFFSET ?
    """, (user_id, limit, offset))
    files = cursor.fetchall()
    conn.close()
    return files

def count_user_files(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM files WHERE user_id=?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def delete_file_db(file_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE file_id=?", (file_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM files")
    total_files = cursor.fetchone()[0]
    conn.close()
    return total_users, total_files

def get_all_user_ids():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids

# --- Pyrogram Client Setup ---
app = Client("FileShareBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

# --- Middleware & Decorators ---
async def check_subscription(client, message):
    if not Config.FORCE_SUB_CHANNEL:
        return True
    try:
        await client.get_chat_member(Config.FORCE_SUB_CHANNEL, message.from_user.id)
    except UserNotParticipant:
        join_url = f"https://t.me/{Config.FORCE_SUB_CHANNEL}"
        await message.reply_text(
            "**You must join our channel to use this bot!**\n\n"
            f"Please join 👉 [{Config.FORCE_SUB_CHANNEL}]({join_url}) 👈 and then try again.",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=join_url)]])
        )
        return False
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        await message.reply_text("Something went wrong. Please try again later.")
        return False
    return True

# --- Command Handlers ---
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    add_user(message.from_user.id)
    if not await check_subscription(client, message):
        return

    # Handle deep linking for file access
    if len(message.command) > 1 and message.command[1].startswith("get_"):
        file_id = message.command[1].split("_", 1)[1]
        db_message_id = get_file_details(file_id)
        if db_message_id:
            try:
                await client.copy_message(
                    chat_id=message.from_user.id,
                    from_chat_id=Config.DB_CHANNEL,
                    message_id=db_message_id
                )
            except Exception as e:
                await message.reply("Could not retrieve file. It may have been deleted. Error: " + str(e))
        else:
            await message.reply("File not found or link is invalid. 🤷‍♂️")
        return
    
    await message.reply_text(
        Config.START_MESSAGE.format(mention=message.from_user.mention),
        disable_web_page_preview=True
    )
    if Config.LOG_CHANNEL:
        await client.send_message(Config.LOG_CHANNEL, f"New User: [{message.from_user.first_name}](tg://user?id={message.from_user.id}) started the bot.")

@app.on_message(filters.command("batch") & filters.private)
async def batch_command(client, message: Message):
    if not await check_subscription(client, message):
        return
    
    user_id = message.from_user.id
    user_batch_mode[user_id] = []
    
    await message.reply_text(
        "**Batch Mode Activated!**\n\n"
        "Send me all the files you want to bundle together. "
        "When you're finished, click the 'Generate Link' button below.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Generate Link", callback_data="batch_done")]])
    )

@app.on_message(filters.command("myfiles") & filters.private)
async def my_files_command(client, message: Message):
    if not await check_subscription(client, message):
        return
    
    user_id = message.from_user.id
    total_files = count_user_files(user_id)
    
    if total_files == 0:
        await message.reply_text("You haven't uploaded any files yet.")
        return
        
    files = get_user_files(user_id, offset=0)
    
    text = f"**Your Uploaded Files (Page 1/{ -(-total_files // 10) }):**\n\n"
    buttons = []
    for file_id, file_name, file_size in files:
        text += f"📄 `{file_name}` ({_format_bytes(file_size)})\n"
        buttons.append([InlineKeyboardButton(f"🗑️ Delete - {file_name[:20]}", callback_data=f"delete_{file_id}")])

    if total_files > 10:
        buttons.append([InlineKeyboardButton("Next Page ➡️", callback_data="page_1")])
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- File Handler ---
@app.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def file_handler(client, message: Message):
    if not await check_subscription(client, message):
        return

    user_id = message.from_user.id
    
    # Handle batch mode
    if user_id in user_batch_mode:
        user_batch_mode[user_id].append(message)
        await message.reply_text(f"File added to batch. You now have {len(user_batch_mode[user_id])} files ready.", quote=True)
        return

    # Handle single file upload
    try:
        sent_message = await message.reply_text("Processing your file...", quote=True)
        
        forwarded_message = await message.forward(Config.DB_CHANNEL)
        db_message_id = forwarded_message.id
        
        file_info = message.document or message.video or message.audio or message.photo
        file_name = getattr(file_info, 'file_name', 'photo.jpg')
        file_type = message.media.value
        file_size = getattr(file_info, 'file_size', 0)

        file_id = save_file(user_id, db_message_id, file_name, file_type, file_size)
        
        bot_username = (await client.get_me()).username
        share_link = f"https://t.me/{bot_username}?start=get_{file_id}"
        
        await sent_message.edit_text(
            f"**File stored successfully!**\n\n"
            f"**File Name:** `{file_name}`\n"
            f"**Share Link:** {share_link}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Share Link", url=share_link)]])
        )
        
        if Config.LOG_CHANNEL:
            await client.send_message(Config.LOG_CHANNEL, f"User [{message.from_user.first_name}](tg://user?id={user_id}) saved file `{file_name}`. Link: {share_link}")

    except Exception as e:
        logger.error(f"Error handling file for {user_id}: {e}")
        await message.reply_text("An error occurred while processing your file. Please try again.")

# --- Callback Query Handlers ---
@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    
    if data == "batch_done":
        if user_id not in user_batch_mode or not user_batch_mode[user_id]:
            await query.answer("You haven't added any files to the batch!", show_alert=True)
            return

        await query.message.edit_text("Generating batch link, please wait...")
        
        file_ids = []
        for msg in user_batch_mode[user_id]:
            forwarded_message = await msg.forward(Config.DB_CHANNEL)
            file_info = msg.document or msg.video or msg.audio or msg.photo
            file_name = getattr(file_info, 'file_name', 'photo.jpg')
            file_type = msg.media.value
            file_size = getattr(file_info, 'file_size', 0)
            file_id = save_file(user_id, forwarded_message.id, file_name, file_type, file_size)
            file_ids.append(file_id)

        # Generate links for each file
        bot_username = (await client.get_me()).username
        links = [f"https://t.me/{bot_username}?start=get_{fid}" for fid in file_ids]
        
        batch_text = "**Batch Upload Complete!**\n\nHere are the links for your files:\n\n"
        for i, link in enumerate(links):
            batch_text += f"{i+1}. {user_batch_mode[user_id][i].document.file_name if user_batch_mode[user_id][i].document else 'Media'}: {link}\n"
        
        await query.message.edit_text(batch_text, disable_web_page_preview=True)
        del user_batch_mode[user_id]
        
    elif data.startswith("page_"):
        page = int(data.split("_")[1])
        total_files = count_user_files(user_id)
        files = get_user_files(user_id, offset=page * 10)
        
        text = f"**Your Uploaded Files (Page {page + 1}/{ -(-total_files // 10) }):**\n\n"
        buttons = []
        for file_id, file_name, file_size in files:
            text += f"📄 `{file_name}` ({_format_bytes(file_size)})\n"
            buttons.append([InlineKeyboardButton(f"🗑️ Delete - {file_name[:20]}", callback_data=f"delete_{file_id}")])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
        if (page + 1) * 10 < total_files:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
            
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except QueryIdInvalid:
            pass # Ignore if user clicks too fast

    elif data.startswith("delete_"):
        file_id = data.split("_")[1]
        await query.message.edit_text(
            "**Are you sure you want to permanently delete this file?**\n\nThis action cannot be undone.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Delete It", callback_data=f"confirm_delete_{file_id}")],
                [InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_delete")]
            ])
        )

    elif data.startswith("confirm_delete_"):
        file_id = data.split("_")[1]
        delete_file_db(file_id)
        await query.message.edit_text("✅ File has been successfully deleted.")

    elif data == "cancel_delete":
        await query.message.delete()
        await query.message.reply_text("Deletion cancelled.")

# --- Admin Commands ---
@app.on_message(filters.command("stats") & filters.user(Config.ADMINS))
async def stats_command(client, message: Message):
    total_users, total_files = get_stats()
    await message.reply_text(
        f"**🤖 Bot Statistics 🤖**\n\n"
        f"**Total Users:** {total_users}\n"
        f"**Total Files Stored:** {total_files}"
    )

@app.on_message(filters.command("broadcast") & filters.user(Config.ADMINS))
async def broadcast_command(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("Please reply to a message to broadcast it.")
        return
    
    user_ids = get_all_user_ids()
    sent_count = 0
    failed_count = 0
    
    status_message = await message.reply_text(f"Broadcasting... Sent: {sent_count}, Failed: {failed_count}")
    
    for user_id in user_ids:
        try:
            await message.reply_to_message.copy(user_id)
            sent_count += 1
        except Exception:
            failed_count += 1
        
        # Edit status message every 20 users
        if (sent_count + failed_count) % 20 == 0:
            await status_message.edit_text(f"Broadcasting... Sent: {sent_count}, Failed: {failed_count}")
        
        await asyncio.sleep(0.1) # Avoid hitting flood limits
        
    await status_message.edit_text(f"**Broadcast Complete!**\n\n**Sent to:** {sent_count} users\n**Failed for:** {failed_count} users")


# --- Helper Functions ---
def _format_bytes(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(size_bytes.bit_length() / 10)
    p = 1024 ** i
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# --- Main Execution ---
if __name__ == "__main__":
    init_db()
    logger.info("Bot is starting...")
    app.run()
    logger.info("Bot has stopped.")
