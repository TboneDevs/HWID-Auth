import os
import re
import time
import logging
import requests
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
RAILWAY_ADD_URL = os.getenv(
    "RAILWAY_ADD_URL",
    "https://web-production-8c5b8.up.railway.app/add"
)

bot = telebot.TeleBot(BOT_TOKEN)

logging.basicConfig(level=logging.INFO)

cooldowns = {}
COOLDOWN_SECONDS = 10


def is_valid_hwid(hwid: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{8,64}", hwid))


def submit_hwid(hwid: str):
    headers = {"Content-Type": "application/json"}
    payload = {"hwid": hwid}

    response = requests.post(
        RAILWAY_ADD_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    try:
        data = response.json()
    except Exception:
        data = {"message": response.text}

    return response.status_code, data


@bot.message_handler(commands=["add"])
def add_hwid(message):
    user_id = message.from_user.id
    now = time.time()

    if user_id in cooldowns and now - cooldowns[user_id] < COOLDOWN_SECONDS:
        wait = int(COOLDOWN_SECONDS - (now - cooldowns[user_id]))
        bot.reply_to(message, f"⏳ Please wait {wait}s before trying again.")
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.reply_to(message, "Usage:\n/add YOUR_HWID")
        return

    hwid = parts[1].strip().lower()

    if not is_valid_hwid(hwid):
        bot.reply_to(
            message,
            "❌ Invalid HWID.\n\nUse only letters a-f and numbers 0-9.\nLength must be 8–64 characters."
        )
        return

    cooldowns[user_id] = now

    try:
        status_code, data = submit_hwid(hwid)

        message_text = str(data.get("message", "")).lower()

        if status_code in (200, 201):
            bot.reply_to(
                message,
                f"✅ HWID submitted successfully!\n\nHWID:\n`{hwid}`\n\nYour device has been added to the whitelist.",
                parse_mode="Markdown"
            )

        elif "already" in message_text or "exists" in message_text:
            bot.reply_to(message, "ℹ️ That HWID is already registered.")

        else:
            bot.reply_to(
                message,
                f"❌ Server error:\n{data.get('message', 'Unknown error')}"
            )

    except requests.exceptions.Timeout:
        logging.exception("Railway request timed out")
        bot.reply_to(message, "❌ Could not reach the whitelist server.\nPlease try again later.")

    except requests.exceptions.RequestException:
        logging.exception("Railway request failed")
        bot.reply_to(message, "❌ Could not reach the whitelist server.\nPlease try again later.")

    except Exception:
        logging.exception("Unexpected bot error")
        bot.reply_to(message, "❌ Something went wrong.\nPlease try again later.")


if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN environment variable")

print("Bot is running...")
bot.infinity_polling()
