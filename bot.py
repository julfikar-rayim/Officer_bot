import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

CONFIG_FILE = "config.json"

# ---------------- LOAD CONFIG ----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            "owner_id": 123456789,
            "allowed_group": -100123456789,
            "word_limit": 20,
            "bad_words": ["fuck", "shit"],
            "allowed_links": ["https://t.me/yourgroup"]
        }
        save_config(config)
        return config
    else:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

config = load_config()

user_warns = {}

# ---------------- OWNER CHECK ----------------
def is_owner(user_id):
    return user_id == config["owner_id"]

# ---------------- HELP ----------------
async def help_cmd(update: Update, context):
    await update.message.reply_text(
        "🛠 *Bot Commands (Customizable)*\n\n"
        "/setlimit 20 → ওয়ার্ড লিমিট সেট\n"
        "/setowner ID → বট ওনার চেঞ্জ\n"
        "/allowgroup CHAT_ID → কোন গ্রুপে কাজ করবে সেট\n"
        "/addbadword WORD → নতুন ব্যাড ওয়ার্ড যোগ\n"
        "/removebadword WORD → ব্যাড ওয়ার্ড রিমুভ\n"
        "/addlink URL → এলাউ লিংক যোগ\n"
        "/removelink URL → এলাউ লিংক রিমুভ\n"
        "/ban @user → ব্যান\n"
        "/unban @user → আনব্যান\n"
        "/id @user → ইউজার আইডি\n",
        parse_mode="Markdown"
    )

# ---------------- SET LIMIT ----------------
async def set_limit(update, context):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("Use: /setlimit NUMBER")

    new_limit = int(context.args[0])
    config["word_limit"] = new_limit
    save_config(config)
    await update.message.reply_text(f"Word limit updated to: {new_limit}")

# ---------------- SET OWNER ----------------
async def set_owner(update, context):
    if not is_owner(update.effective_user.id):
        return
    
    if not context.args:
        return await update.message.reply_text("Use: /setowner USER_ID")

    new_owner = int(context.args[0])
    config["owner_id"] = new_owner
    save_config(config)
    await update.message.reply_text(f"Owner changed to: {new_owner}")

# ---------------- SET ALLOWED GROUP ----------------
async def allow_group(update, context):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("Use: /allowgroup GROUP_ID")

    new_group = int(context.args[0])
    config["allowed_group"] = new_group
    save_config(config)
    await update.message.reply_text(f"Allowed group set to: {new_group}")

# ---------------- ADD BAD WORD ----------------
async def add_bad(update, context):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        return

    word = context.args[0].lower()
    config["bad_words"].append(word)
    save_config(config)

    await update.message.reply_text(f"Added bad word: {word}")

# ---------------- REMOVE BAD WORD ----------------
async def remove_bad(update, context):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        return

    word = context.args[0].lower()

    if word in config["bad_words"]:
        config["bad_words"].remove(word)
        save_config(config)
        await update.message.reply_text(f"Removed bad word: {word}")

# ---------------- ADD LINK ----------------
async def add_link(update, context):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        return

    link = context.args[0]
    config["allowed_links"].append(link)
    save_config(config)

    await update.message.reply_text(f"Allowed link added: {link}")

# ---------------- REMOVE LINK ----------------
async def remove_link(update, context):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        return

    link = context.args[0]

    if link in config["allowed_links"]:
        config["allowed_links"].remove(link)
        save_config(config)

        await update.message.reply_text(f"Removed allowed link: {link}")

# ---------------- BAN USER ----------------
async def ban_cmd(update, context):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("Use: /ban @user")

    try:
        user = await context.bot.get_chat(context.args[0])
        await update.effective_chat.ban_member(user.id)
        await update.message.reply_text(f"🚫 Banned: {user.full_name}")
    except:
        await update.message.reply_text("Error banning user.")

# ---------------- UNBAN ----------------
async def unban_cmd(update, context):
    if not is_owner(update.effective_user.id):
        return

    try:
        user = await context.bot.get_chat(context.args[0])
        await update.effective_chat.unban_member(user.id)
        await update.message.reply_text(f"Unbanned: {user.full_name}")
    except:
        pass

# ---------------- ID ----------------
async def id_cmd(update, context):
    if not context.args:
        return await update.message.reply_text("Use: /id @username")

    try:
        user = await context.bot.get_chat(context.args[0])
        await update.message.reply_text(f"User ID: {user.id}")
    except:
        await update.message.reply_text("User not found.")

# ---------------- AUTO FILTER ----------------
async def filter_handler(update, context):
    if update.effective_chat.id != config["allowed_group"]:
        return

    user = update.effective_user.id
    msg = update.message

    # Owner exempt
    if user == config["owner_id"]:
        return

    # Word limit
    if msg.text and len(msg.text.split()) > config["word_limit"]:
        await warn_user(update, context, user, "Message too long.")
        await msg.delete()
        return

    # Bad words
    if msg.text:
        lower = msg.text.lower()
        for w in config["bad_words"]:
            if w in lower:
                await warn_user(update, context, user, "Bad word detected.")
                return

    # Link filter
    if msg.entities:
        for e in msg.entities:
            if e.type == "url":
                url = msg.text[e.offset:e.offset + e.length]
                if url not in config["allowed_links"]:
                    await warn_user(update, context, user, "Link not allowed.")
                    await msg.delete()
                    return

# ---------------- WARN SYSTEM ----------------
async def warn_user(update, context, user, reason):
    user_warns[user] = user_warns.get(user, 0) + 1
    await update.message.reply_text(f"⚠ Warning {user_warns[user]}/3\nReason: {reason}")

    if user_warns[user] >= 3:
        await update.effective_chat.ban_member(user)
        await update.message.reply_text("🚫 User banned after 3 warnings.")

# ---------------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("setlimit", set_limit))
app.add_handler(CommandHandler("setowner", set_owner))
app.add_handler(CommandHandler("allowgroup", allow_group))
app.add_handler(CommandHandler("addbadword", add_bad))
app.add_handler(CommandHandler("removebadword", remove_bad))
app.add_handler(CommandHandler("addlink", add_link))
app.add_handler(CommandHandler("removelink", remove_link))
app.add_handler(CommandHandler("ban", ban_cmd))
app.add_handler(CommandHandler("unban", unban_cmd))
app.add_handler(CommandHandler("id", id_cmd))

app.add_handler(MessageHandler(filters.ALL, filter_handler))

app.run_polling()
