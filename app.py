import os
import json
import telebot
import threading
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))

# 改成你的 Telegram User ID
OWNER_ID = 6527570402

bot = telebot.TeleBot(BOT_TOKEN)

CONFIG_FILE = "targets.json"
albums = defaultdict(list)
timers = {}

def load_targets():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_targets(targets):
    with open(CONFIG_FILE, "w") as f:
        json.dump(targets, f)

def is_admin(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]
        return message.from_user.id in admin_ids
    except:
        return False

def is_owner(message):
    return message.from_user.id == OWNER_ID

@bot.message_handler(commands=["settopic"])
def set_topic(message):

    if not is_admin(message):
        bot.reply_to(message, "❌ Only admins can use this command.")
        return

    topic_id = getattr(message, "message_thread_id", None)

    targets = load_targets()

    new_target = {
        "chat_id": message.chat.id,
        "topic_id": topic_id
    }

    if new_target not in targets:
        targets.append(new_target)
        save_targets(targets)

    bot.reply_to(
        message,
        f"✅ Added forward target!\nChat ID: {message.chat.id}\nTopic ID: {topic_id}\nTotal targets: {len(targets)}"
    )

@bot.message_handler(commands=["listtopics"])
def list_topics(message):

    if not is_admin(message):
        bot.reply_to(message, "❌ Only admins can use this command.")
        return

    targets = load_targets()

    if not targets:
        bot.reply_to(message, "No forward targets set.")
        return

    text = "📌 Forward targets:\n\n"

    for i, t in enumerate(targets, 1):
        text += f"{i}. Chat ID: {t['chat_id']} | Topic ID: {t['topic_id']}\n"

    bot.reply_to(message, text)

@bot.message_handler(commands=["clearall"])
def clear_all(message):

    if not is_owner(message):
        bot.reply_to(message, "❌ Only bot owner can use this command.")
        return

    save_targets([])

    bot.reply_to(
        message,
        "✅ All saved forward topics have been cleared."
    )

def forward_to_all(message_ids):

    targets = load_targets()

    for target in targets:

        chat_id = target["chat_id"]
        topic_id = target["topic_id"]

        try:
            if len(message_ids) == 1:

                bot.forward_message(
                    chat_id=chat_id,
                    from_chat_id=SOURCE_CHAT_ID,
                    message_id=message_ids[0],
                    message_thread_id=topic_id
                )

            else:

                bot.forward_messages(
                    chat_id=chat_id,
                    from_chat_id=SOURCE_CHAT_ID,
                    message_ids=message_ids,
                    message_thread_id=topic_id
                )

        except Exception as e:
            print(f"Forward failed to {chat_id}/{topic_id}: {e}")

def send_album(media_group_id):

    messages = albums.pop(media_group_id, [])
    timers.pop(media_group_id, None)

    if messages:
        forward_to_all(sorted(messages))

@bot.message_handler(content_types=[
    "photo",
    "video",
    "document",
    "audio",
    "voice",
    "sticker",
    "text"
])
def handle_message(message):

    if message.chat.id != SOURCE_CHAT_ID:
        return

    if getattr(message, "media_group_id", None):

        group_id = message.media_group_id

        albums[group_id].append(message.message_id)

        if group_id in timers:
            timers[group_id].cancel()

        timer = threading.Timer(
            5.0,
            send_album,
            args=[group_id]
        )

        timers[group_id] = timer
        timer.start()

    else:

        forward_to_all([message.message_id])

print("Bot started...")

bot.infinity_polling()
