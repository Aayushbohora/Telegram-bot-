import os
import json
import re
import requests
from telegram import Update, ChatMemberUpdated
from telegram.constants import ChatType
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          ContextTypes, filters, ChatMemberHandler)
from flask import Flask
from threading import Thread

# ✅ Flask keep-alive for Replit
app = Flask('')


@app.route('/')
def home():
    return "I'm alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


Thread(target=run).start()

# ✅ API keys
OPENROUTER_API_KEY = "Your ai api"
TELEGRAM_BOT_TOKEN = "Your bot token"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "mistralai/mistral-7b-instruct"

# ✅ Learning memory file
MEMORY_FILE = "memory.json"

# Load memory if exists
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, 'r') as f:
        memory = json.load(f)
else:
    memory = {}

# ✅ Save to memory
def learn_and_save(question, answer):
    memory[question.lower()] = answer
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f)

# ✅ Welcome on group add
async def welcome_on_add(update: ChatMemberUpdated,
                         context: ContextTypes.DEFAULT_TYPE):
    new_member = update.chat_member.new_chat_member
    if new_member.user.id == context.bot.id:
        await context.bot.send_message(chat_id=update.chat_member.chat.id,
                                       text="Thanks for letting me in 😎")

# ✅ Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Yo! I'm your AI homie 🤖\nChat with me anytime.")

# ✅ Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_input = msg.text.strip()

    if not user_input or msg.from_user.is_bot:
        return

    chat_type = msg.chat.type
    bot_user = await context.bot.get_me()
    bot_username = f"@{bot_user.username}"

    # Only respond in groups if mentioned or replied to
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        mentioned = bot_username.lower() in user_input.lower()
        replied = msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.id == bot_user.id
        if not (mentioned or replied):
            return
        if mentioned:
            user_input = re.sub(bot_username,
                                "",
                                user_input,
                                flags=re.IGNORECASE).strip()

    # ✅ If remembered before
    if user_input.lower() in memory:
        await msg.reply_text(memory[user_input.lower()],
                             reply_to_message_id=msg.message_id)
        return

    # ✅ SYSTEM PROMPT
    system_prompt = (
        "You are a smart, casual Gen-Z bot named Nepsi in Telegram. "
        "Talk short, chill, funny like a real teenager. Use emojis, slang, but only where natural. "
        "If user says 'who made you', 'who created you', or 'creator', then say 'Created by @Nepomodz 🧠🔥'. "
        "DO NOT mention creator in other replies. Respond based on user's message, not randomly. "
        "Never repeat yourself, never say the same thing twice. Always try to match the user's vibe."
        "it should be short and easy to understand"
        "you should not create a long reply if user asks a long question")

    # ✅ Prepare request
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://example.com",
        "X-Title": "NepX Bot"
    }

    data = {
        "model": MODEL_NAME,
        "messages": [{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": user_input
        }]
    }

    try:
        res = requests.post(API_URL, headers=headers, json=data, timeout=15)
        result = res.json()

        if "choices" in result:
            reply = result["choices"][0]["message"]["content"].strip()
        elif "error" in result:
            reply = f"⚠️ API Error: {result['error']['message']}"
        else:
            reply = "Huh? 🤔 Try again."

    except Exception as e:
        reply = f"❌ Error: {str(e)}"

    # Save learning
    if len(reply) < 200:
        learn_and_save(user_input, reply)

    await msg.reply_text(reply, reply_to_message_id=msg.message_id)

# ✅ Run the bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        ChatMemberHandler(welcome_on_add, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running...")
    app.run_polling()
