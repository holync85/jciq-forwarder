import os
import telebot
import threading
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN")

SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
TARGET_TOPIC_ID = int(os.getenv("TARGET_TOPIC_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

albums = defaultdict(list)
timers = {}

def send_album(media_group_id):
    messages = albums.pop(media_group_id, [])
    timers.pop(media_group_id, None)

    if not messages:
        return

    message_ids = sorted(messages)

    bot.forward_messages(
        chat_id=TARGET_CHAT_ID,
        from_chat_id=SOURCE_CHAT_ID,
        message_ids=message_ids,
        message_thread_id=TARGET_TOPIC_ID
    )

@bot.message_handler(content_types=[
    "photo", "video", "document", "audio", "voice", "sticker", "text"
])
def forward_message(message):
    if message.chat.id != SOURCE_CHAT_ID:
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
            chat_id=TARGET_CHAT_ID,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=message.message_id,
            message_thread_id=TARGET_TOPIC_ID
        )

print("Bot started...")
bot.infinity_polling()
