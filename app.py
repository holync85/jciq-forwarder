import os
import json
import telebot
import threading
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

CONFIG_FILE = "config.json"
albums = defaultdict(list)
timers = {}

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

def get_target():
    data = load_config()
    return data.get("target_chat_id"), data.get("target_topic_id")

@bot.message_handler(commands=["settopic"])
def set_topic(message):
    topic_id = getattr(message, "message_thread_id", None)

    data = {
        "target_chat_id": message.chat.id,
        "target_topic_id": topic_id
    }
    save_config(data)

    bot.reply_to(
        message,
        f"✅ Forward target set!\nChat ID: {message.chat.id}\nTopic ID: {topic_id}"
    )

def send_album(media_group_id):
    messages = albums.pop(media_group_id, [])
    timers.pop(media_group_id, None)

    if not messages:
        return

    target_chat_id, target_topic_id = get_target()

    if not target_chat_id:
        return

    bot.forward_messages(
        chat_id=target_chat_id,
        from_chat_id=SOURCE_CHAT_ID,
        message_ids=sorted(messages),
        message_thread_id=target_topic_id
    )

@bot.message_handler(content_types=[
    "photo", "video", "document", "audio", "voice", "sticker", "text"
])
def forward_message(message):
    if message.chat.id != SOURCE_CHAT_ID:
        return

    target_chat_id, target_topic_id = get_target()

    if not target_chat_id:
        return

    if getattr(message, "media_group_id", None):
        group_id = message.media_group_id
        albums[group_id].append(message.message_id)

        if group_id in timers:
            timers[group_id].cancel()

        timer = threading.Timer(5.0, send_album, args=[group_id])
        timers[group_id] = timer
        timer.start()

    else:
        bot.forward_message(
            chat_id=target_chat_id,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=message.message_id,
            message_thread_id=target_topic_id
        )

print("Bot started...")
bot.infinity_polling()
