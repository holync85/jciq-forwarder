import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")

async def forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await context.bot.forward_message(
            chat_id=int(TARGET_CHAT_ID),
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.ALL, forwarder))

app.run_polling()