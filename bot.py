import asyncio, requests, threading, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events
from telethon.sessions import StringSession

SESSION = os.environ["SESSION"]
GEMINI_KEY = os.environ["GEMINI_KEY"]
API_HASH = os.environ["API_HASH"]
API_ID = int(os.environ["API_ID"])
GROUP_ID = int(os.environ["GROUP_ID"])
BOT_IDS = [int(x) for x in os.environ["BOT_IDS"].split(",")]
WAIT = int(os.environ.get("WAIT", "0"))
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

def ask_ai(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_KEY}"
    body = {"contents": [{"parts": [{"text": text}]}]}
    r = requests.post(url, json=body, timeout=40)
    try:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        print("AI ERROR:", r.status_code, r.text[:300])
        return None

@client.on(events.NewMessage(chats=GROUP_ID, from_users=BOT_IDS))
async def handler(event):
    text = event.raw_text
    if not text:
        return
    print("New msg:", text[:50])
    if WAIT:
        await asyncio.sleep(WAIT)
        msgs = await client.get_messages(GROUP_ID, min_id=event.id, limit=50)
        for m in msgs:
            if m.reply_to and m.reply_to.reply_to_msg_id == event.id:
                return
    reply = await asyncio.to_thread(ask_ai, text)
    if reply:
        await event.reply(reply)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass

def run_server():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever()

threading.Thread(target=run_server, daemon=True).start()
client.start()
print("Bot running")
client.run_until_disconnected()
