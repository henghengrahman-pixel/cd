import asyncio
import json
import os
import logging
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- Logging ---
logging.basicConfig(
    format='[%(levelname)5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)

# --- ENV (WAJIB) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

if not API_ID or not API_HASH or not SESSION_STRING:
    raise RuntimeError("❌ ENV belum lengkap: API_ID / API_HASH / SESSION_STRING")

# --- Client ---
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- Data File ---
DATA_FILE = 'bot_data.json'

def load_data():
    default_data = {
        "caption": "",
        "groups": [],
        "is_active": False,
        "media_message_id": None,
        "buttons": [],
        "forward_link": None
    }

    if not os.path.exists(DATA_FILE):
        return default_data

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default_data

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

bot_data = load_data()

# --- Flask (Uptime Ping Railway) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Bot aktif dan online!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# --- Broadcast Loop ---
async def broadcast_loop():
    while bot_data['is_active']:
        for group in bot_data['groups']:
            if not bot_data['is_active']:
                break

            try:
                if bot_data['caption']:
                    await client.send_message(group, bot_data['caption'])
                    await client.send_message("me", f"✅ Broadcast ke {group}")
            except Exception as e:
                await client.send_message("me", f"❌ Gagal kirim ke {group}: {e}")

            await asyncio.sleep(180)

        if bot_data['is_active']:
            await asyncio.sleep(1800)

# --- Commands ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^/on$'))
async def start_broadcast(event):
    if not bot_data['is_active']:
        bot_data['is_active'] = True
        save_data(bot_data)
        await event.respond("✅ Broadcast dimulai.")
        asyncio.create_task(broadcast_loop())
    else:
        await event.respond("⚠️ Broadcast sudah berjalan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/off$'))
async def stop_broadcast(event):
    bot_data['is_active'] = False
    save_data(bot_data)
    await event.respond("⛔ Broadcast dihentikan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/addgroup (@\w+)$'))
async def add_group(event):
    group = event.pattern_match.group(1).lower()

    if group not in bot_data['groups']:
        bot_data['groups'].append(group)
        save_data(bot_data)
        await event.respond(f"✅ Grup {group} ditambahkan.")
    else:
        await event.respond("⚠️ Grup sudah ada.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/listgroup$'))
async def list_group(event):
    if not bot_data['groups']:
        await event.respond("📭 Belum ada grup yang ditambahkan.")
    else:
        daftar = "\n".join(bot_data['groups'])
        await event.respond(f"📋 Grup terdaftar:\n{daftar}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/status$'))
async def status(event):
    status_text = "✅ AKTIF" if bot_data['is_active'] else "❌ NONAKTIF"
    await event.respond(f"📡 Broadcast: {status_text}\n📦 Grup: {len(bot_data['groups'])}")

# --- Run ---
async def main():
    await client.start()
    logging.info("✅ Bot Connected")

    if bot_data['is_active']:
        asyncio.create_task(broadcast_loop())

    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"❌ Error utama: {e}")
