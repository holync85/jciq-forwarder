import os
import json
import time
import telebot
import threading
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 6527570402

SOURCE_CHAT_IDS = {
    "1": int(os.getenv("SOURCE_CHAT_ID_1")),
    "2": int(os.getenv("SOURCE_CHAT_ID_2")),
    "3": int(os.getenv("SOURCE_CHAT_ID_3")),
    "4": int(os.getenv("SOURCE_CHAT_ID_4")),
}

bot = telebot.TeleBot(BOT_TOKEN)

albums = defaultdict(list)
timers = {}

def config_file(group_no):
    return f"targets_{group_no}.json"

def load_targets(group_no):
    try:
        with open(config_file(group_no), "r") as f:
            return json.load(f)
    except:
        return []

def save_targets(group_no, targets):
    with open(config_file(group_no), "w") as f:
        json.dump(targets, f)

def is_admin(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        return message.from_user.id in [a.user.id for a in admins]
    except:
        return False

def is_owner(message):
    return message.from_user.id == OWNER_ID

def is_admin_or_owner(message):
    return is_admin(message) or is_owner(message)

def get_group_no(message):
    parts = message.text.split()

    if len(parts) < 2:
        return None

    group_no = parts[1]

    if group_no not in SOURCE_CHAT_IDS:
        return None

    return group_no

# =========================
# /settopic
# =========================
@bot.message_handler(commands=["settopic"])
def set_topic(message):

    if not is_admin_or_owner(message):
        bot.reply_to(
            message,
            "❌ Only admins or owner can use this command."
        )
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(
            message,
            "❌ Use:\n/settopic 1\n/settopic 2\n/settopic 3\n/settopic 4"
        )
        return

    topic_id = getattr(message, "message_thread_id", None)

    targets = load_targets(group_no)

    new_target = {
        "chat_id": message.chat.id,
        "topic_id": topic_id
    }

    if new_target not in targets:
        targets.append(new_target)
        save_targets(group_no, targets)

    bot.reply_to(
        message,
        f"✅ Topic added!\n\n"
        f"Source: {group_no}\n"
        f"Chat ID: {message.chat.id}\n"
        f"Topic ID: {topic_id}\n"
        f"Total targets: {len(targets)}"
    )

# =========================
# /listtopic
# =========================
@bot.message_handler(commands=["listtopic"])
def list_topic(message):

    if not is_admin_or_owner(message):
        bot.reply_to(
            message,
            "❌ Only admins or owner can use this command."
        )
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(
            message,
            "❌ Use:\n/listtopic 1\n/listtopic 2\n/listtopic 3\n/listtopic 4"
        )
        return

    targets = load_targets(group_no)

    if not targets:
        bot.reply_to(
            message,
            f"❌ No topics saved for Source {group_no}."
        )
        return

    text = f"📌 Saved Topics For Source {group_no}\n\n"

    for i, t in enumerate(targets, 1):

        text += (
            f"{i}.\n"
            f"Chat ID: {t['chat_id']}\n"
            f"Topic ID: {t['topic_id']}\n\n"
        )

    bot.reply_to(message, text)

# =========================
# /removetopic
# =========================
@bot.message_handler(commands=["removetopic", "removetoppic"])
def remove_topic(message):

    if not is_admin_or_owner(message):
        bot.reply_to(
            message,
            "❌ Only admins or owner can use this command."
        )
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(
            message,
            "❌ Use:\n/removetopic 1\n/removetopic 2\n/removetopic 3\n/removetopic 4"
        )
        return

    topic_id = getattr(message, "message_thread_id", None)

    targets = load_targets(group_no)

    before = len(targets)

    targets = [
        t for t in targets
        if not (
            int(t["chat_id"]) == int(message.chat.id)
            and str(t["topic_id"]) == str(topic_id)
        )
    ]

    save_targets(group_no, targets)

    if len(targets) < before:

        bot.reply_to(
            message,
            f"✅ Topic removed from Source {group_no}."
        )

    else:

        bot.reply_to(
            message,
            "❌ Topic not found."
        )

# =========================
# /clearall
# =========================
@bot.message_handler(commands=["clearall"])
def clear_all(message):

    if not is_owner(message):
        bot.reply_to(
            message,
            "❌ Only bot owner can use this command."
        )
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(
            message,
            "❌ Use:\n/clearall 1\n/clearall 2\n/clearall 3\n/clearall 4"
        )
        return

    topic_id = getattr(message, "message_thread_id", None)

    if not topic_id:
        bot.reply_to(
            message,
            "❌ Use this inside a topic."
        )
        return

    deleted = 0

    latest_id = message.message_id

    for msg_id in range(latest_id, latest_id - 5000, -1):

        try:

            bot.delete_message(
                chat_id=message.chat.id,
                message_id=msg_id
            )

            deleted += 1

            time.sleep(0.03)

        except:
            pass

    bot.send_message(
        chat_id=message.chat.id,
        text=f"✅ Deleted {deleted} messages.",
        message_thread_id=topic_id
    )

# =========================
# FORWARD
# =========================
def forward_to_targets(group_no, message_ids):

    targets = load_targets(group_no)

    source_chat_id = SOURCE_CHAT_IDS[group_no]

    for target in targets:

        try:

            if len(message_ids) == 1:

                bot.forward_message(
                    chat_id=target["chat_id"],
                    from_chat_id=source_chat_id,
                    message_id=message_ids[0],
                    message_thread_id=target["topic_id"]
                )

            else:

                bot.forward_messages(
                    chat_id=target["chat_id"],
                    from_chat_id=source_chat_id,
                    message_ids=message_ids,
                    message_thread_id=target["topic_id"]
                )

        except Exception as e:

            print(f"Forward failed Source {group_no}: {e}")

# =========================
# SEND ALBUM
# =========================
def send_album(key):

    group_no, media_group_id = key

    messages = albums.pop(key, [])

    timers.pop(key, None)

    if messages:

        forward_to_targets(
            group_no,
            sorted(messages)
        )

# =========================
# MESSAGE HANDLER
# =========================
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

    group_no = None

    for no, chat_id in SOURCE_CHAT_IDS.items():

        if message.chat.id == chat_id:

            group_no = no

            break

    if not group_no:
        return

    # ALBUM
    if getattr(message, "media_group_id", None):

        key = (
            group_no,
            message.media_group_id
        )

        albums[key].append(
            message.message_id
        )

        if key in timers:
            timers[key].cancel()

        timer = threading.Timer(
            5.0,
            send_album,
            args=[key]
        )

        timers[key] = timer

        timer.start()

    # SINGLE MESSAGE
    else:

        forward_to_targets(
            group_no,
            [message.message_id]
        )

print("Bot started...")

bot.infinity_polling()
