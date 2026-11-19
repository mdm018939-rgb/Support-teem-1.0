import asyncio, requests, threading, os, sys, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events
from telethon.sessions import StringSession

def log(*a):
    print(*a, flush=True)

SESSION = os.environ["SESSION"]
GEMINI_KEY = os.environ["GEMINI_KEY"]
API_HASH = os.environ["API_HASH"]
API_ID = int(os.environ["API_ID"])
GROUP_ID = int(os.environ["GROUP_ID"])
BOT_IDS = [int(x) for x in os.environ["BOT_IDS"].split(",")]
WAIT = int(os.environ.get("WAIT", "0"))
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

PROMPT = os.environ.get("PROMPT", """তুমি একজন বন্ধুসুলভ কাস্টমার সাপোর্ট সহকারী।
নিয়ম:
- ইউজার যে ভাষায় লেখে (বাংলা/ইংরেজি) সেই ভাষায় উত্তর দাও।
- উত্তর ছোট, পরিষ্কার ও ভদ্র রাখো (সর্বোচ্চ ৩-৪ লাইন)।
- না জানলে বানিয়ে বলো না। বলো "এডমিন শীঘ্রই আপনাকে জানাবেন"।
- টাকা, পাসওয়ার্ড, ওটিপি চাইবে না।
- সালাম দিলে সালামের উত্তর দাও।""")

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

def ask_ai(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_KEY}"
    body = {
        "system_instruction": {"parts": [{"text": PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
    }
    try:
        r = requests.post(url, json=body, timeout=40)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        try:
            log("AI ERROR:", r.status_code, r.text[:300])
        except Exception:
            log("AI ERROR:", repr(e))
        return None

@client.on(events.NewMessage(chats=GROUP_ID))
async def handler(event):
    log("GROUP MSG from:", event.sender_id, "|", (event.raw_text or "")[:40])
    if event.sender_id not in BOT_IDS:
        return
    text = event.raw_text
    if not text:
        log("খালি টেক্সট, স্কিপ")
        return
    if WAIT:
        await asyncio.sleep(WAIT)
        msgs = await client.get_messages(GROUP_ID, min_id=event.id, limit=50)
        for m in msgs:
            if m.reply_to and m.reply_to.reply_to_msg_id == event.id:
                log("কেউ রিপ্লাই দিয়েছে, AI স্কিপ")
                return
    reply = await asyncio.to_thread(ask_ai, text)
    if reply:
        await event.reply(reply)
        log("Replied")

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass

def run_server():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever()

async def main():
    log("Connecting to Telegram...")
    await client.connect()
    if not await client.is_user_authorized():
        log("SESSION ERROR: লগইন হয়নি, SESSION বাতিল বা ভুল। নতুন SESSION বানান।")
        return
    await client.get_dialogs()
    me = await client.get_me()
    log("Logged in as:", me.id, me.first_name)
    try:
        await client.send_message(GROUP_ID, "✅ AI বট চালু হয়েছে (টেস্ট)")
        log("Test message sent to group")
    except Exception as e:
        log("GROUP ERROR: গ্রুপে মেসেজ পাঠানো যায়নি:", repr(e))
    log("Bot running")
    await client.run_until_disconnected()

threading.Thread(target=run_server, daemon=True).start()

try:
    asyncio.run(main())
except Exception:
    log("FATAL ERROR:")
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    import time
    time.sleep(3600)
