import os
import json
import time
import base64
import requests
import telebot
import threading
from collections import defaultdict
from deep_translator import GoogleTranslator

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

albums = defaultdict(list)
timers = {}

MESSAGE_LOG_FILE = "message_logs.json"
TRANSLATE_SETTING_FILE = "translate_settings.json"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def github_get_file(filename):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    r = requests.get(url, headers=HEADERS)

    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]

    return None, None

def github_save_file(filename, content):
    old_data, sha = github_get_file(filename)

    encoded = base64.b64encode(
        json.dumps(content, indent=2).encode()
    ).decode()

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"

    payload = {
        "message": f"Update {filename}",
        "content": encoded
    }

    if sha:
        payload["sha"] = sha

    requests.put(url, headers=HEADERS, json=payload)

def load_targets(group_no):
    data, sha = github_get_file(f"targets_{group_no}.json")
    return data if data else []

def save_targets(group_no, targets):
    github_save_file(f"targets_{group_no}.json", targets)

def load_message_logs():
    data, sha = github_get_file(MESSAGE_LOG_FILE)
    return data if data else {}

def save_message_logs(data):
    github_save_file(MESSAGE_LOG_FILE, data)

def log_sent_message(chat_id, topic_id, message_id):
    logs = load_message_logs()
    key = f"{chat_id}:{topic_id}"

    if key not in logs:
        logs[key] = []

    logs[key].append(message_id)
    save_message_logs(logs)

def load_translate_settings():
    data, sha = github_get_file(TRANSLATE_SETTING_FILE)
    return data if data else {}

def save_translate_settings(data):
    github_save_file(TRANSLATE_SETTING_FILE, data)

def get_chat_topic_key(message):
    topic_id = getattr(message, "message_thread_id", None)
    return f"{message.chat.id}:{topic_id}"

def translate_text(text, source, target):
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        return f"❌ Translate error: {e}"

def has_thai(text):
    return any("\u0E00" <= c <= "\u0E7F" for c in text)

def has_chinese(text):
    return any("\u4e00" <= c <= "\u9fff" for c in text)

def has_english(text):
    return any("a" <= c.lower() <= "z" for c in text)

def has_vietnamese(text):
    chars = "ăâđêôơưÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴáàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"
    return any(c in chars for c in text)

def is_owner(message):
    return message.from_user.id == OWNER_ID

def is_admin(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        return message.from_user.id in [a.user.id for a in admins]
    except:
        return False

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

@bot.message_handler(commands=["settopic"])
def settopic(message):
    if not is_admin_or_owner(message):
        bot.reply_to(message, "❌ Only admins or owner can use this command.")
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(message, "❌ Use: /settopic 1 / 2 / 3 / 4")
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
        f"✅ Topic added!\nSource: {group_no}\nChat ID: {message.chat.id}\nTopic ID: {topic_id}\nTotal targets: {len(targets)}"
    )

@bot.message_handler(commands=["listtopic"])
def listtopic(message):
    if not is_admin_or_owner(message):
        bot.reply_to(message, "❌ Only admins or owner can use this command.")
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(message, "❌ Use: /listtopic 1 / 2 / 3 / 4")
        return

    targets = load_targets(group_no)

    if not targets:
        bot.reply_to(message, "❌ No topic saved.")
        return

    text = f"📌 Saved Topics For Source {group_no}\n\n"

    for i, t in enumerate(targets, 1):
        text += f"{i}.\nChat ID: {t['chat_id']}\nTopic ID: {t['topic_id']}\n\n"

    bot.reply_to(message, text)

@bot.message_handler(commands=["removetopic", "removetoppic"])
def removetopic(message):
    if not is_admin_or_owner(message):
        bot.reply_to(message, "❌ Only admins or owner can use this command.")
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(message, "❌ Use: /removetopic 1 / 2 / 3 / 4")
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
        bot.reply_to(message, f"✅ Topic removed from Source {group_no}.")
    else:
        bot.reply_to(message, "❌ Topic not found.")

@bot.message_handler(commands=["clearall"])
def clearall(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Only bot owner can use this command.")
        return

    group_no = get_group_no(message)

    if not group_no:
        bot.reply_to(message, "❌ Use: /clearall 1 / 2 / 3 / 4")
        return

    topic_id = getattr(message, "message_thread_id", None)
    logs = load_message_logs()
    key = f"{message.chat.id}:{topic_id}"
    message_ids = logs.get(key, [])

    deleted = 0

    for msg_id in message_ids:
        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
            time.sleep(0.01)
        except:
            pass

    logs[key] = []
    save_message_logs(logs)

    bot.send_message(
        chat_id=message.chat.id,
        text=f"✅ Topic cleared.\nDeleted: {deleted}",
        message_thread_id=topic_id
    )

@bot.message_handler(commands=["clearfull"])
def clearfull(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Only bot owner can use this command.")
        return

    latest_id = message.message_id
    deleted = 0

    bot.reply_to(message, "🗑 Clearing full group messages...")

    for msg_id in range(latest_id, latest_id - 1000, -1):
        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
            time.sleep(0.01)
        except:
            pass

    bot.send_message(
        chat_id=message.chat.id,
        text=f"✅ Full group clear done.\nDeleted: {deleted}"
    )

@bot.message_handler(commands=["autothai"])
def autothai(message):
    if not is_admin_or_owner(message):
        bot.reply_to(message, "❌ Only admins or owner can use this command.")
        return

    parts = message.text.split()

    if len(parts) < 2 or parts[1].lower() not in ["on", "off"]:
        bot.reply_to(message, "Use: /autothai on 或 /autothai off")
        return

    settings = load_translate_settings()
    key = get_chat_topic_key(message)

    if key not in settings:
        settings[key] = {}

    settings[key]["thai"] = parts[1].lower() == "on"
    save_translate_settings(settings)

    bot.reply_to(message, f"✅ Auto Thai translation: {parts[1].upper()}")

@bot.message_handler(commands=["autovi"])
def autovi(message):
    if not is_admin_or_owner(message):
        bot.reply_to(message, "❌ Only admins or owner can use this command.")
        return

    parts = message.text.split()

    if len(parts) < 2 or parts[1].lower() not in ["on", "off"]:
        bot.reply_to(message, "Use: /autovi on 或 /autovi off")
        return

    settings = load_translate_settings()
    key = get_chat_topic_key(message)

    if key not in settings:
        settings[key] = {}

    settings[key]["vi"] = parts[1].lower() == "on"
    save_translate_settings(settings)

    bot.reply_to(message, f"✅ Auto Vietnamese translation: {parts[1].upper()}")

def auto_translate(message):
    if not message.text:
        return

    if message.text.startswith("/"):
        return

    settings = load_translate_settings()
    key = get_chat_topic_key(message)
    mode = settings.get(key, {})

    text = message.text

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
            bot.reply_to(message, f"🇨🇳 中文 → 🇹🇭 Thai:\n{th}")

        elif has_english(text):
            th = translate_text(text, "en", "th")
            bot.reply_to(message, f"🇬🇧 English → 🇹🇭 Thai:\n{th}")

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
            bot.reply_to(message, f"🇨🇳 中文 → 🇻🇳 Vietnamese:\n{vi}")

        elif has_english(text):
            vi = translate_text(text, "en", "vi")
            bot.reply_to(message, f"🇬🇧 English → 🇻🇳 Vietnamese:\n{vi}")

def forward_to_targets(group_no, message_ids):
    targets = load_targets(group_no)
    source_chat_id = SOURCE_CHAT_IDS[group_no]

    for target in targets:
        try:
            if len(message_ids) == 1:
                sent = bot.forward_message(
                    chat_id=target["chat_id"],
                    from_chat_id=source_chat_id,
                    message_id=message_ids[0],
                    message_thread_id=target["topic_id"]
                )

                log_sent_message(
                    target["chat_id"],
                    target["topic_id"],
                    sent.message_id
                )

            else:
                sent_msgs = bot.forward_messages(
                    chat_id=target["chat_id"],
                    from_chat_id=source_chat_id,
                    message_ids=message_ids,
                    message_thread_id=target["topic_id"]
                )

                for s in sent_msgs:
                    log_sent_message(
                        target["chat_id"],
                        target["topic_id"],
                        s.message_id
                    )

        except Exception as e:
            print(e)

def send_album(key):
    group_no, media_group_id = key
    msgs = albums.pop(key, [])
    timers.pop(key, None)

    if msgs:
        forward_to_targets(group_no, sorted(msgs))

@bot.message_handler(content_types=[
    "text",
    "photo",
    "video",
    "document",
    "audio",
    "voice",
    "sticker"
])
def handle_message(message):
    auto_translate(message)

    group_no = None

    for no, cid in SOURCE_CHAT_IDS.items():
        if message.chat.id == cid:
            group_no = no
            break

    if not group_no:
        return

    if getattr(message, "media_group_id", None):
        key = (group_no, message.media_group_id)
        albums[key].append(message.message_id)

        if key in timers:
            timers[key].cancel()

        timer = threading.Timer(5.0, send_album, args=[key])
        timers[key] = timer
        timer.start()
    else:
        forward_to_targets(group_no, [message.message_id])

print("Bot running...")
bot.infinity_polling()
