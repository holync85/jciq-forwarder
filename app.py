import os
import json
import base64
import requests
import telebot
import threading
from collections import defaultdict
from telebot.types import InputMediaPhoto, InputMediaVideo
from deep_translator import MyMemoryTranslator

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 6527570402

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

SOURCE_CHAT_IDS = {
    "1": int(os.getenv("SOURCE_CHAT_ID_1")),
    "2": int(os.getenv("SOURCE_CHAT_ID_2")),
    "3": int(os.getenv("SOURCE_CHAT_ID_3")),
    "4": int(os.getenv("SOURCE_CHAT_ID_4")),
}

bot = telebot.TeleBot(BOT_TOKEN)

CONFIG_FILE = "targets.json"
TRANSLATE_FILE = "translate_settings.json"

albums = defaultdict(list)
timers = {}

ALBUM_DELAY = 0.5


# =========================
# GITHUB SAVE/LOAD
# =========================

def github_get_file(path):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        }

        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(content)

    except:
        pass

    return {}


def github_save_file(path, content_json):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        }

        old_sha = None

        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            old_sha = r.json()["sha"]

        content = base64.b64encode(
            json.dumps(content_json, indent=2).encode()
        ).decode()

        payload = {
            "message": f"Update {path}",
            "content": content,
            "branch": "main"
        }

        if old_sha:
            payload["sha"] = old_sha

        requests.put(url, headers=headers, json=payload)

    except Exception as e:
        print(e)


def load_targets():
    return github_get_file(CONFIG_FILE)


def save_targets(data):
    github_save_file(CONFIG_FILE, data)


def load_translate_settings():
    return github_get_file(TRANSLATE_FILE)


def save_translate_settings(data):
    github_save_file(TRANSLATE_FILE, data)


# =========================
# HELPERS
# =========================

def get_chat_topic_key(message):
    topic_id = getattr(message, "message_thread_id", 0)
    return f"{message.chat.id}_{topic_id}"


def is_admin(chat_id, user_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False


def is_admin_or_owner(message):
    return (
        is_admin(message.chat.id, message.from_user.id)
        or message.from_user.id == OWNER_ID
    )


def has_thai(text):
    return any("\u0E00" <= c <= "\u0E7F" for c in text)


def has_chinese(text):
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def has_english(text):
    return any(c.isalpha() and ord(c) < 128 for c in text)


def has_vietnamese(text):
    chars = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    return any(c in chars for c in text.lower())


# =========================
# TRANSLATE
# =========================

def translate_text(text, source, target):
    try:
        return MyMemoryTranslator(
            source=source,
            target=target
        ).translate(text)

    except Exception as e:
        return f"⚠️ Translate busy:\n{e}"


def auto_translate(message):
    if not message.text:
        return

    if message.text.startswith("/"):
        return

    settings = load_translate_settings()

    key = get_chat_topic_key(message)

    mode = settings.get(key, {})

    text = message.text

    # THAI
    if mode.get("thai"):

        if has_thai(text):

            en = translate_text(text, "th", "en")
            zh = translate_text(text, "th", "zh-CN")

            bot.reply_to(
                message,
                f"🇹🇭 Thai\n\n🇬🇧 English:\n{en}\n\n🇨🇳 中文:\n{zh}"
            )

        elif has_chinese(text):

            th = translate_text(text, "zh-CN", "th")

            bot.reply_to(
                message,
                f"🇨🇳 中文 → 🇹🇭 Thai:\n{th}"
            )

        elif has_english(text):

            th = translate_text(text, "en", "th")

            bot.reply_to(
                message,
                f"🇬🇧 English → 🇹🇭 Thai:\n{th}"
            )

    # VIETNAMESE
    if mode.get("vi"):

        if has_vietnamese(text):

            en = translate_text(text, "vi", "en")
            zh = translate_text(text, "vi", "zh-CN")

            bot.reply_to(
                message,
                f"🇻🇳 Vietnamese\n\n🇬🇧 English:\n{en}\n\n🇨🇳 中文:\n{zh}"
            )

        elif has_chinese(text):

            vi = translate_text(text, "zh-CN", "vi")

            bot.reply_to(
                message,
                f"🇨🇳 中文 → 🇻🇳 Vietnamese:\n{vi}"
            )

        elif has_english(text):

            vi = translate_text(text, "en", "vi")

            bot.reply_to(
                message,
                f"🇬🇧 English → 🇻🇳 Vietnamese:\n{vi}"
            )


# =========================
# AUTO TRANSLATE COMMANDS
# =========================

@bot.message_handler(commands=["autothai"])
def autothai(message):

    if not is_admin_or_owner(message):
        return

    args = message.text.split()

    if len(args) < 2:
        bot.reply_to(message, "Use: /autothai on/off")
        return

    settings = load_translate_settings()

    key = get_chat_topic_key(message)

    if args[1].lower() == "on":

        settings[key] = {"thai": True}

        save_translate_settings(settings)

        bot.reply_to(message, "✅ Auto Thai translation ON")

    else:

        settings.pop(key, None)

        save_translate_settings(settings)

        bot.reply_to(message, "❌ Auto Thai translation OFF")


@bot.message_handler(commands=["autovi"])
def autovi(message):

    if not is_admin_or_owner(message):
        return

    args = message.text.split()

    if len(args) < 2:
        bot.reply_to(message, "Use: /autovi on/off")
        return

    settings = load_translate_settings()

    key = get_chat_topic_key(message)

    if args[1].lower() == "on":

        settings[key] = {"vi": True}

        save_translate_settings(settings)

        bot.reply_to(message, "✅ Auto Vietnamese translation ON")

    else:

        settings.pop(key, None)

        save_translate_settings(settings)

        bot.reply_to(message, "❌ Auto Vietnamese translation OFF")


# =========================
# TOPIC COMMANDS
# =========================

@bot.message_handler(commands=["settopic"])
def settopic(message):

    if not is_admin_or_owner(message):
        return

    args = message.text.split()

    if len(args) < 2:
        bot.reply_to(message, "Use: /settopic 1/2/3/4")
        return

    source_key = args[1]

    if source_key not in SOURCE_CHAT_IDS:
        return

    targets = load_targets()

    key = get_chat_topic_key(message)

    targets[key] = {
        "chat_id": message.chat.id,
        "topic_id": getattr(message, "message_thread_id", 0),
        "source": source_key
    }

    save_targets(targets)

    bot.reply_to(
        message,
        f"✅ Topic added!\n\n"
        f"Chat ID: {message.chat.id}\n"
        f"Topic ID: {getattr(message, 'message_thread_id', 0)}\n"
        f"Source: {source_key}\n"
        f"Total targets: {len(targets)}"
    )


@bot.message_handler(commands=["listtopic"])
def listtopic(message):

    if not is_admin_or_owner(message):
        return

    targets = load_targets()

    text = "📋 Topic List\n\n"

    for k, v in targets.items():

        text += (
            f"Chat: {v['chat_id']}\n"
            f"Topic: {v['topic_id']}\n"
            f"Source: {v['source']}\n\n"
        )

    bot.reply_to(message, text)


@bot.message_handler(commands=["removetopic", "removetoppic"])
def removetopic(message):

    if not is_admin_or_owner(message):
        return

    targets = load_targets()

    key = get_chat_topic_key(message)

    if key in targets:

        del targets[key]

        save_targets(targets)

        bot.reply_to(message, "✅ Topic removed")

    else:

        bot.reply_to(message, "❌ Topic not found")


# =========================
# CLEAR TOPIC
# =========================

@bot.message_handler(commands=["clearall"])
def clearall(message):

    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only owner can use this")
        return

    topic_id = getattr(message, "message_thread_id", None)

    if not topic_id:
        bot.reply_to(message, "❌ Use inside topic")
        return

    bot.reply_to(message, "🗑 Clearing topic messages...")

    deleted = 0

    start_id = message.message_id - 5000
    end_id = message.message_id + 500

    for msg_id in range(start_id, end_id + 1):

        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except:
            pass

    bot.send_message(
        message.chat.id,
        f"✅ Topic clear done\nDeleted: {deleted}",
        message_thread_id=topic_id
    )


# =========================
# CLEAR FULL GROUP
# =========================

@bot.message_handler(commands=["clearfull"])
def clearfull(message):

    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only owner can use this")
        return

    bot.reply_to(message, "🗑 Clearing full group...")

    deleted = 0

    start_id = message.message_id - 5000
    end_id = message.message_id + 500

    for msg_id in range(start_id, end_id + 1):

        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except:
            pass

    bot.send_message(
        message.chat.id,
        f"✅ FULL GROUP CLEAR DONE\nDeleted: {deleted}"
    )


# =========================
# ALBUM SEND
# =========================

def send_album(media_group_id):

    items = albums[media_group_id]

    if not items:
        return

    targets = load_targets()

    first = items[0]

    source_chat_id = first.chat.id

    media = []

    caption = first.caption if hasattr(first, "caption") else None

    for msg in items:

        if msg.content_type == "photo":

            media.append(
                InputMediaPhoto(
                    media=msg.photo[-1].file_id,
                    caption=caption if len(media) == 0 else ""
                )
            )

        elif msg.content_type == "video":

            media.append(
                InputMediaVideo(
                    media=msg.video.file_id,
                    caption=caption if len(media) == 0 else ""
                )
            )

    for target in targets.values():

        if SOURCE_CHAT_IDS[target["source"]] != source_chat_id:
            continue

        try:

            bot.send_media_group(
                target["chat_id"],
                media,
                message_thread_id=target["topic_id"]
            )

        except Exception as e:
            print(e)

    albums.pop(media_group_id, None)


# =========================
# MEDIA HANDLER
# =========================

@bot.message_handler(content_types=["photo", "video"])
def media_handler(message):

    auto_translate(message)

    media_group_id = message.media_group_id

    if media_group_id:

        albums[media_group_id].append(message)

        if media_group_id in timers:
            timers[media_group_id].cancel()

        timers[media_group_id] = threading.Timer(
            ALBUM_DELAY,
            send_album,
            args=[media_group_id]
        )

        timers[media_group_id].start()

    else:

        targets = load_targets()

        for target in targets.values():

            if SOURCE_CHAT_IDS[target["source"]] != message.chat.id:
                continue

            try:

                if message.photo:

                    bot.send_photo(
                        target["chat_id"],
                        message.photo[-1].file_id,
                        caption=message.caption,
                        message_thread_id=target["topic_id"]
                    )

                elif message.video:

                    bot.send_video(
                        target["chat_id"],
                        message.video.file_id,
                        caption=message.caption,
                        message_thread_id=target["topic_id"]
                    )

            except Exception as e:
                print(e)


# =========================
# TEXT FORWARD
# =========================

@bot.message_handler(func=lambda m: True)
def text_handler(message):

    auto_translate(message)

    targets = load_targets()

    for target in targets.values():

        if SOURCE_CHAT_IDS[target["source"]] != message.chat.id:
            continue

        try:

            bot.forward_message(
                target["chat_id"],
                message.chat.id,
                message.message_id,
                message_thread_id=target["topic_id"]
            )

        except Exception as e:
            print(e)


print("Bot running...")
bot.infinity_polling(skip_pending=True)
