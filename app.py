import os
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
TARGET_TOPIC_ID = int(os.getenv("TARGET_TOPIC_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(content_types=[
    "text", "photo", "video", "document", "audio", "voice", "sticker"
])
def forward_message(message):
    if message.chat.id != SOURCE_CHAT_ID:
        return

    bot.forward_message(
        chat_id=TARGET_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        message_thread_id=TARGET_TOPIC_ID
    )

print("Bot started...")
bot.infinity_polling()
