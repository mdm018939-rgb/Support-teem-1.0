import asyncio, requests, threading, os, sys, traceback, time
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

MODELS = [m.strip() for m in os.environ.get(
    "MODEL", "gemini-3.5-flash-lite,gemini-3.6-flash,gemini-3.8-flash"
).split(",")]

PROMPT = os.environ.get("PROMPT", """তুমি একটি সাপোর্ট টিমের হয়ে ইউজারদের মেসেজের উত্তর দিচ্ছ। এডমিন এখন অনলাইনে নেই।

নিয়ম:
1. ইউজার যে ভাষায় লেখে (বাংলা, ইংরেজি বা বাংলিশ), সেই ভাষাতেই উত্তর দাও।
2. উত্তর ছোট, সহজ ও ভদ্র রাখো (সর্বোচ্চ ৩-৪ লাইন)।
3. সালাম দিলে সালামের উত্তর দাও। ধন্যবাদ দিলে ভদ্রভাবে উত্তর দাও।
4. যা জানো না, তা বানিয়ে বলবে না। বলবে: "আপনার মেসেজটি এডমিনকে জানানো হয়েছে, তিনি অনলাইনে এসে শীঘ্রই উত্তর দেবেন।"
5. কখনো টাকা, পাসওয়ার্ড, ওটিপি বা ব্যক্তিগত তথ্য চাইবে না।
6. দাম, পেমেন্ট, রিফান্ড, ডেলিভারি সময়ের মতো জরুরি বিষয়ে নিজে থেকে কিছু নিশ্চিত করবে না। বলবে এডমিন জানাবেন।
7. তুমি যে AI সেটা জিজ্ঞেস করলে সত্য বলবে: "আমি এডমিনের স্বয়ংক্রিয় সহকারী।"
8. কেউ রাগ করলে বা অভিযোগ করলে শান্তভাবে দুঃখ প্রকাশ করে বলবে এডমিনকে জানানো হয়েছে।""")

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

def ask_ai(text):
    last_err = ""
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"}
        body = {
            "system_instruction": {"parts": [{"text": PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
        }
        r = None
        try:
            r = requests.post(url, headers=headers, json=body, timeout=40)
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            if r is not None:
                last_err = f"{model} -> {r.status_code} {r.text[:200]}"
            else:
                last_err = f"{model} -> {repr(e)}"
            log("AI ERROR:", last_err)
    return "⚠️ AI ERROR: " + last_err

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
        await client.send_message(GROUP_ID, "✅ AI বট চালু হয়েছে")
        log("Start message sent to group")
    except Exception as e:
        log("GROUP ERROR:", repr(e))
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
    time.sleep(3600)
