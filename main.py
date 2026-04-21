import asyncio
import json
import os
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
import threading

# --- Logging ---
logging.basicConfig(
    format='[%(levelname)5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)

# --- ENV ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

if not API_ID or not API_HASH or not SESSION_STRING:
    raise RuntimeError("❌ ENV belum lengkap")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- DATA ---
DATA_FILE = 'bot_data.json'

def load_data():
    default = {
        "caption": "",
        "groups": [],
        "is_active": False,
        "media_message_id": None
    }

    if not os.path.exists(DATA_FILE):
        return default

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

bot_data = load_data()

# 🔥 FIX ANTI DOUBLE LOOP
broadcast_task = None

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Bot aktif"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# --- BROADCAST ---
async def broadcast_loop():
    global broadcast_task

    while bot_data['is_active']:

        for group in bot_data['groups']:

            if not bot_data['is_active']:
                break

            try:
                if bot_data['media_message_id']:
                    msg = await client.get_messages("me", ids=bot_data['media_message_id'])

                    if msg and msg.media:
                        await client.send_file(
                            group,
                            msg.media,
                            caption=bot_data['caption'] or msg.message or ""
                        )

                        await client.send_message("me", f"✅ Media ke {group} sukses")
                    else:
                        await client.send_message("me", f"❌ Media tidak ditemukan")

                elif bot_data['caption']:
                    await client.send_message(group, bot_data['caption'])
                    await client.send_message("me", f"✅ Text ke {group} sukses")

            except Exception as e:
                await client.send_message("me", f"❌ Gagal ke {group}: {e}")

            await asyncio.sleep(180)

        if bot_data['is_active']:
            await asyncio.sleep(1800)

    # loop berhenti
    broadcast_task = None

# ================= COMMAND =================

# ON
@client.on(events.NewMessage(outgoing=True, pattern=r'^/on$'))
async def start(event):
    global broadcast_task

    if bot_data['is_active']:
        return await event.respond("⚠️ Sudah ON")

    bot_data['is_active'] = True
    save_data(bot_data)

    # 🔥 FIX: hanya buat 1 loop
    if not broadcast_task or broadcast_task.done():
        broadcast_task = asyncio.create_task(broadcast_loop())

    await event.respond("✅ Broadcast ON")

# OFF
@client.on(events.NewMessage(outgoing=True, pattern=r'^/off$'))
async def stop(event):
    bot_data['is_active'] = False
    save_data(bot_data)
    await event.respond("⛔ Broadcast OFF")

# ADD GROUP MULTI
@client.on(events.NewMessage(outgoing=True, pattern=r'^/addgroup'))
async def addgroup(event):
    lines = event.raw_text.split('\n')[1:]

    added = []
    for g in lines:
        g = g.strip()

        if g.startswith("@") and g not in bot_data['groups']:
            bot_data['groups'].append(g)
            added.append(g)

    save_data(bot_data)

    if added:
        await event.respond("✅ Grup ditambahkan:\n" + "\n".join(added))
    else:
        await event.respond("⚠️ Tidak ada grup baru")

# LIST
@client.on(events.NewMessage(outgoing=True, pattern=r'^/listgroup$'))
async def listgroup(event):
    if not bot_data['groups']:
        await event.respond("📭 Kosong")
    else:
        await event.respond("\n".join(bot_data['groups']))

# STATUS
@client.on(events.NewMessage(outgoing=True, pattern=r'^/status$'))
async def status(event):
    status_text = "ON" if bot_data['is_active'] else "OFF"
    await event.respond(f"📡 Status: {status_text}\n📦 Total Grup: {len(bot_data['groups'])}")

# SET MEDIA
@client.on(events.NewMessage(outgoing=True, pattern=r'^/setmedia$'))
async def setmedia(event):
    if not event.is_reply:
        return await event.respond("⚠️ Reply media dulu")

    msg = await event.get_reply_message()

    if not msg.media:
        return await event.respond("❌ Ini bukan media")

    bot_data['media_message_id'] = msg.id
    bot_data['caption'] = msg.message or ""
    save_data(bot_data)

    await event.respond("✅ Media + caption disimpan")

# SET CAPTION
@client.on(events.NewMessage(outgoing=True, pattern=r'^/setcaption'))
async def setcaption(event):
    text = event.raw_text.replace("/setcaption", "").strip()

    bot_data['caption'] = text
    save_data(bot_data)

    await event.respond("✅ Caption diupdate")

# ================= RUN =================
async def main():
    global broadcast_task

    await client.start()
    logging.info("✅ Bot Connected")

    # 🔥 FIX: hanya 1 loop saat start
    if bot_data['is_active']:
        if not broadcast_task or broadcast_task.done():
            broadcast_task = asyncio.create_task(broadcast_loop())

    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
