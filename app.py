import os
import telebot
import time
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN")

SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
TARGET_TOPIC_ID = int(os.getenv("TARGET_TOPIC_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

media_groups = defaultdict(list)

@bot.message_handler(content_types=[
    "photo", "video", "document"
])
def handle_album(message):

    if message.chat.id != SOURCE_CHAT_ID:
        return

    # Album
    if message.media_group_id:

        media_groups[message.media_group_id].append(message.message_id)

        time.sleep(2)

        ids = media_groups.pop(message.media_group_id, [])

        if ids:
            bot.forward_messages(
                chat_id=TARGET_CHAT_ID,
                from_chat_id=SOURCE_CHAT_ID,
                message_ids=ids,
                message_thread_id=TARGET_TOPIC_ID
            )

    else:
        bot.forward_message(
            chat_id=TARGET_CHAT_ID,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=message.message_id,
            message_thread_id=TARGET_TOPIC_ID
        )

@bot.message_handler(func=lambda m: True)
def handle_text(message):

    if message.chat.id != SOURCE_CHAT_ID:
        return

    bot.forward_message(
        chat_id=TARGET_CHAT_ID,
        from_chat_id=SOURCE_CHAT_ID,
        message_id=message.message_id,
        message_thread_id=TARGET_TOPIC_ID
    )

print("Bot started...")
bot.infinity_polling()
