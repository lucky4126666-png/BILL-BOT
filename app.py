import os, json, asyncio, uuid
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", OWNER_ID))
API_KEY = os.getenv("API_KEY", "secret123")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "123456")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== FILE =====
DATA_FILE = "data.json"
ADMIN_FILE = "admins.json"
BANNED_FILE = "banned.json"
SCHEDULE_FILE = "schedule.json"

# ===== LOAD SAVE SAFE =====
def load_json(file, default):
    try:
        if not os.path.exists(file): return default
        with open(file) as f: return json.load(f)
    except:
        return default

def save_json(file, data):
    try:
        with open(file,"w") as f: json.dump(data,f)
    except: pass

def load_list(file):
    try:
        if not os.path.exists(file): return set()
        with open(file) as f: return set(json.load(f))
    except: return set()

def save_list(file,data):
    try:
        with open(file,"w") as f: json.dump(list(data),f)
    except: pass

keywords = load_json(DATA_FILE, {})
ADMIN_IDS = load_list(ADMIN_FILE)
BANNED_IDS = load_list(BANNED_FILE)
schedules = load_json(SCHEDULE_FILE, [])

# ===== LOGIN =====
SESSIONS = set()

def check_login(request):
    return request.cookies.get("session") in SESSIONS

def check_api(request):
    return request.headers.get("x-api-key") == API_KEY

# ===== TIME =====
def get_now():
    return datetime.utcnow() + timedelta(hours=7)

# ===== PERMISSION =====
def is_admin(uid):
    return uid == OWNER_ID or uid in ADMIN_IDS

def is_banned(uid):
    return uid in BANNED_IDS

# ===== BUTTON =====
def build_buttons(text):
    if not text: return None
    rows, row = [], []
    for line in text.split("\n"):
        if "|" not in line: continue
        try:
            name,url=line.split("|",1)
            row.append(InlineKeyboardButton(text=name.strip(),url=url.strip()))
            if len(row)==2:
                rows.append(row); row=[]
        except: continue
    if row: rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ===== SEND SAFE =====
async def send_job(job):
    try:
        markup = build_buttons(job.get("button"))
        text = str(job.get("text") or "")

        if job.get("image"):
            await bot.send_photo(job["chat_id"], job["image"], caption=text, reply_markup=markup)
        else:
            await bot.send_message(job["chat_id"], text, reply_markup=markup)
    except Exception as e:
        print("SEND ERROR:", e)

# ===== BOT =====
@dp.message(Command("start"))
async def start(m: types.Message):
    if not is_admin(m.from_user.id): return
    await m.answer("🚀 BOT READY")

@dp.message()
async def handle(m: types.Message):
    uid = m.from_user.id
    if is_banned(uid) or not is_admin(uid): return

    text = (m.text or "").strip().lower()

    if text in keywords:
        await send_job({
            "chat_id": m.chat.id,
            **keywords[text]
        })
    else:
        await m.answer("⚠️ Không có dữ liệu")

# ===== SCHEDULER =====
last_sent = {}

async def scheduler():
    while True:
        now_dt = get_now()
        now = now_dt.strftime("%H:%M")

        for job in list(schedules):
            try:
                jid = job.get("id") or str(uuid.uuid4())
                job["id"] = jid

                if last_sent.get(jid) == now:
                    continue

                interval = job.get("interval") or 0

                if interval:
                    if now_dt.minute % int(interval) != 0:
                        continue
                else:
                    if job.get("time") != now:
                        continue

                await send_job(job)
                last_sent[jid] = now

                if not job.get("repeat") and not interval:
                    schedules.remove(job)

            except Exception as e:
                print("SCHEDULE ERROR:", e)

        save_json(SCHEDULE_FILE, schedules)
        await asyncio.sleep(30)

async def safe_scheduler():
    while True:
        try:
            await scheduler()
        except Exception as e:
            print("CRASH:", e)
            await asyncio.sleep(5)

# ===== API =====
async def api_add_keyword(request):
    if not check_api(request):
        return web.json_response({"error":"no auth"})
    data = await request.json()
    keywords[data["key"]] = data
    save_json(DATA_FILE, keywords)
    return web.json_response({"status":"ok"})

async def api_list_keyword(request):
    return web.json_response(keywords)

async def api_del_keyword(request):
    if not check_api(request):
        return web.json_response({"error":"no auth"})
    data = await request.json()
    keywords.pop(data["key"], None)
    save_json(DATA_FILE, keywords)
    return web.json_response({"status":"deleted"})

async def api_add_schedule(request):
    if not check_api(request):
        return web.json_response({"error":"no auth"})
    data = await request.json()

    if not data.get("chat_id"):
        return web.json_response({"error":"missing chat_id"})

    job = {
        "id": str(uuid.uuid4()),
        "chat_id": int(data.get("chat_id", TARGET_CHAT_ID)),
        "text": data.get("text"),
        "image": data.get("image"),
        "button": data.get("button"),
        "time": data.get("time"),
        "interval": data.get("interval"),
        "repeat": data.get("repeat", False)
    }

    schedules.append(job)
    save_json(SCHEDULE_FILE, schedules)
    return web.json_response(job)

async def api_list_schedule(request):
    return web.json_response(schedules)

async def api_del_schedule(request):
    if not check_api(request):
        return web.json_response({"error":"no auth"})
    data = await request.json()
    global schedules
    schedules = [s for s in schedules if s["id"] != data["id"]]
    save_json(SCHEDULE_FILE, schedules)
    return web.json_response({"status":"deleted"})

async def api_send(request):
    if not check_api(request):
        return web.json_response({"error":"no auth"})
    data = await request.json()
    await send_job(data)
    return web.json_response({"status":"sent"})

# ===== WEB UI =====
async def login_page(request):
    return web.Response(text="<form method='post'><input name='user'><input name='pass'><button>Login</button></form>", content_type="text/html")

async def login_post(request):
    data = await request.post()
    if data.get("user")==ADMIN_USER and data.get("pass")==ADMIN_PASS:
        sid=str(uuid.uuid4())
        SESSIONS.add(sid)
        resp=web.HTTPFound("/admin")
        resp.set_cookie("session",sid)
        return resp
    return web.Response(text="❌ Sai")

async def admin_page(request):
    if not check_login(request):
        raise web.HTTPFound("/login")

    html = f"""
    <html><body style="background:#0f172a;color:white;font-family:sans-serif">
    <h1>🚀 DASHBOARD</h1>

    <h3>📅 Schedule ({len(schedules)})</h3>
    {''.join([f"<p>{s.get('time')} | {s.get('text')} <a href='/del_schedule?id={s.get('id')}'>❌</a></p>" for s in schedules])}

    <form action="/add_schedule">
    <input name="chat_id" placeholder="Chat ID"><br>
    <input name="time" placeholder="HH:MM"><br>
    <input name="interval" placeholder="Interval phút"><br>
    <input name="text" placeholder="Nội dung"><br>
    <input name="image" placeholder="file_id"><br>
    <textarea name="button"></textarea><br>
    <label>Lặp</label><input type="checkbox" name="repeat"><br>
    <button>Tạo</button></form>

    </body></html>
    """
    return web.Response(text=html, content_type="text/html")

# ===== ROUTES =====
app = web.Application()

app.router.add_post("/api/keyword/add", api_add_keyword)
app.router.add_get("/api/keyword/list", api_list_keyword)
app.router.add_post("/api/keyword/delete", api_del_keyword)

app.router.add_post("/api/schedule/add", api_add_schedule)
app.router.add_get("/api/schedule/list", api_list_schedule)
app.router.add_post("/api/schedule/delete", api_del_schedule)

app.router.add_post("/api/send", api_send)

app.router.add_get("/login", login_page)
app.router.add_post("/login", login_post)
app.router.add_get("/admin", admin_page)

# ===== START =====
async def start_bot(app):
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(safe_scheduler())

app.on_startup.append(start_bot)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
