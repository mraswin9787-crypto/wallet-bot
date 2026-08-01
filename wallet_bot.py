import os
import json
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
PASSWORD = os.getenv("PASSWORD", "mysecret123")
DATA_FILE = "wallet_data.json"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"items": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Wallet Bot Ready!\n\n"
        "🔒 Password போட்டா stored files கிடைக்கும்.\n"
        "Owner மட்டும் files அனுப்ப முடியும்.\n"
        "⚠️ Files local-ல save ஆகாது — file_id மட்டும் store ஆகும்."
    )

async def handle_owner_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return

    message = update.message
    data = load_data()
    item = {"type": None, "file_id": None, "text": None, "file_name": None}

    try:
        if message.video:
            item["type"] = "video"
            item["file_id"] = message.video.file_id
            item["file_name"] = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
        elif message.document:
            item["type"] = "document"
            item["file_id"] = message.document.file_id
            item["file_name"] = message.document.file_name or f"doc_{message.document.file_unique_id}"
        elif message.photo:
            item["type"] = "photo"
            item["file_id"] = message.photo[-1].file_id
            item["file_name"] = f"photo_{message.photo[-1].file_unique_id}.jpg"
        elif message.text:
            item["type"] = "text"
            item["text"] = message.text
        else:
            await message.reply_text("இந்த type support இல்லை.")
            return

        data["items"].append(item)
        save_data(data)
        await message.reply_text(f"✅ Saved (file_id only)! Total items: {len(data['items'])}")

    except Exception as e:
        logger.error(e)
        await message.reply_text(f"Error: {e}")

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text != PASSWORD:
        return

    data = load_data()
    items = data.get("items", [])

    if not items:
        await update.message.reply_text("📭 Storage empty.")
        return

    await update.message.reply_text(f"🔓 Password correct! Sending {len(items)} items...")

    for item in items:
        try:
            if item["type"] == "video":
                await context.bot.send_video(chat_id=update.effective_chat.id, video=item["file_id"])
            elif item["type"] == "document":
                await context.bot.send_document(chat_id=update.effective_chat.id, document=item["file_id"])
            elif item["type"] == "photo":
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=item["file_id"])
            elif item["type"] == "text":
                await context.bot.send_message(chat_id=update.effective_chat.id, text=item["text"])
        except Exception as e:
            logger.error(f"Failed to send item: {e}")

    await update.message.reply_text("✅ All items sent!")

async def clear_storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    save_data({"items": []})
    await update.message.reply_text("🗑️ Storage cleared!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    data = load_data()
    await update.message.reply_text(f"📦 Total items stored: {len(data['items'])}")

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN environment variable not set!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_storage))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(MessageHandler(
        filters.User(OWNER_ID) & (filters.VIDEO | filters.Document.ALL | filters.PHOTO | filters.TEXT),
        handle_owner_media
    ))

    app.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_password))

    print("Bot is running on Railway...")
    app.run_polling()

if __name__ == "__main__":
    main()
