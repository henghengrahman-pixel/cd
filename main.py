import asyncio
import json
import os
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
import threading

# --- Logging ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.WARNING)

# --- ENV ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- Data ---
DATA_FILE = 'bot_data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "caption": "",
            "groups": [],
            "is_active": False,
            "media_message_id": None
        }
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

bot_data = load_data()

# --- Flask ---
app = Flask(__name__)
@app.route('/')
def index():
    return "✅ Bot aktif"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# --- BROADCAST ---
async def broadcast_loop():
    while bot_data['is_active']:
        for group in bot_data['groups']:
            try:
                if bot_data['media_message_id']:
                    msg = await client.get_messages("me", ids=bot_data['media_message_id'])

                    await client.send_file(
                        group,
                        msg.media,
                        caption=bot_data['caption']
                    )

                    await client.send_message("me", f"✅ Media ke {group} sukses.")

                elif bot_data['caption']:
                    await client.send_message(group, bot_data['caption'])
                    await client.send_message("me", f"✅ Text ke {group} sukses.")

            except Exception as e:
                await client.send_message("me", f"❌ Gagal kirim ke {group}: {e}")

            await asyncio.sleep(180)

        await asyncio.sleep(1800)

# --- COMMANDS ---

# ON
@client.on(events.NewMessage(outgoing=True, pattern=r'^/on$'))
async def start(event):
    bot_data['is_active'] = True
    save_data(bot_data)
    await event.respond("✅ Broadcast ON")
    asyncio.create_task(broadcast_loop())

# OFF
@client.on(events.NewMessage(outgoing=True, pattern=r'^/off$'))
async def stop(event):
    bot_data['is_active'] = False
    save_data(bot_data)
    await event.respond("⛔ Broadcast OFF")

# ADD GROUP MULTI
@client.on(events.NewMessage(outgoing=True, pattern=r'^/addgroup'))
async def addgroup(event):
    text = event.raw_text.split('\n')[1:]

    added = []
    for g in text:
        g = g.strip()
        if g.startswith("@") and g not in bot_data['groups']:
            bot_data['groups'].append(g)
            added.append(g)

    save_data(bot_data)

    await event.respond(f"✅ Grup ditambahkan:\n{', '.join(added)}")

# LIST
@client.on(events.NewMessage(outgoing=True, pattern=r'^/listgroup$'))
async def listgroup(event):
    if not bot_data['groups']:
        await event.respond("Kosong")
    else:
        await event.respond("\n".join(bot_data['groups']))

# STATUS
@client.on(events.NewMessage(outgoing=True, pattern=r'^/status$'))
async def status(event):
    await event.respond(f"Status: {'ON' if bot_data['is_active'] else 'OFF'}\nTotal Grup: {len(bot_data['groups'])}")

# SET MEDIA (REPLY)
@client.on(events.NewMessage(outgoing=True, pattern=r'^/setmedia$'))
async def setmedia(event):
    if not event.is_reply:
        return await event.respond("Reply media dulu")

    msg = await event.get_reply_message()

    if not msg.media:
        return await event.respond("Bukan media")

    bot_data['media_message_id'] = msg.id
    bot_data['caption'] = msg.text or ""
    save_data(bot_data)

    await event.respond("✅ Media disimpan")

# SET CAPTION
@client.on(events.NewMessage(outgoing=True, pattern=r'^/setcaption'))
async def setcaption(event):
    text = event.raw_text.replace("/setcaption", "").strip()
    bot_data['caption'] = text
    save_data(bot_data)

    await event.respond("✅ Caption disimpan")

# --- RUN ---
async def main():
    await client.start()
    print("✅ Bot Connected")

    if bot_data['is_active']:
        asyncio.create_task(broadcast_loop())

    await client.run_until_disconnected()

asyncio.run(main())
