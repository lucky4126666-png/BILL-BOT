import os, json, asyncio, uuid
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
API_KEY = os.getenv("API_KEY", "secret123")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "123456")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

r = redis.from_url(REDIS_URL, decode_responses=True)

# ===== FILE =====
DATA_FILE = "data.json"
SCHEDULE_FILE = "schedule.json"

# ===== LOAD SAVE =====
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

keywords = load_json(DATA_FILE, {})
schedules = load_json(SCHEDULE_FILE, [])

# ===== TIME =====
def get_now():
    return datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=7))
    )

# ===== SECURITY =====
def check_api(request):
    return request.headers.get("x-api-key") == API_KEY

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

# ===== STATS =====
stats = {"sent":0,"error":0}

# ===== QUEUE =====
def push_queue(job):
    try:
        r.lpush("bot_queue", json.dumps(job))
    except:
        print("REDIS ERROR")

# ===== SEND =====
async def send_job(job):
    try:
        markup = build_buttons(job.get("button"))
        text = str(job.get("text") or "")

        if job.get("image"):
            await bot.send_photo(job["chat_id"], job["image"], caption=text, reply_markup=markup)
        else:
            await bot.send_message(job["chat_id"], text, reply_markup=markup)

        stats["sent"] += 1

    except Exception as e:
        stats["error"] += 1
        print("SEND ERROR:", e)

# ===== WORKER =====
async def worker():
    while True:
        try:
            data = r.brpop("bot_queue", timeout=5)

            if not data:
                await asyncio.sleep(1)
                continue

            job = json.loads(data[1])
            await send_job(job)

            await asyncio.sleep(0.05)

        except Exception as e:
            print("WORKER ERROR:", e)
            await asyncio.sleep(1)

# ===== BOT =====
@dp.message(Command("start"))
async def start(m: types.Message):
    if m.from_user.id != OWNER_ID: return
    await m.answer("🚀 BOT READY")

@dp.message()
async def handle(m: types.Message):
    text = (m.text or "").lower()

    if text in keywords:
        push_queue({
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

                push_queue(job)
                last_sent[jid] = now

                if not job.get("repeat") and not interval:
                    schedules.remove(job)

            except Exception as e:
                print("SCHEDULE ERROR:", e)

        if len(last_sent) > 5000:
            last_sent.clear()

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

async def api_add_schedule(request):
    if not check_api(request):
        return web.json_response({"error":"no auth"})

    data = await request.json()

    job = {
        "id": str(uuid.uuid4()),
        "chat_id": int(data["chat_id"]),
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

async def api_send(request):
    if not check_api(request):
        return web.json_response({"error":"no auth"})

    data = await request.json()
    push_queue(data)

    return web.json_response({"status":"queued"})

async def api_stats(request):
    return web.json_response(stats)

# ===== DASHBOARD =====
async def admin_page(request):
    html = f"""
    <html><body style="background:#0f172a;color:white;font-family:sans-serif">

    <h1>🚀 DASHBOARD</h1>

    <h3>📊 Stats</h3>
    <p>Sent: {stats["sent"]}</p>
    <p>Error: {stats["error"]}</p>

    <h3>📅 Schedule ({len(schedules)})</h3>
    {''.join([f"<p>{s.get('time')} | {s.get('text')}</p>" for s in schedules])}

    </body></html>
    """
    return web.Response(text=html, content_type="text/html")

# ===== ROUTES =====
app = web.Application()

app.router.add_post("/api/keyword/add", api_add_keyword)
app.router.add_get("/api/keyword/list", api_list_keyword)

app.router.add_post("/api/schedule/add", api_add_schedule)
app.router.add_get("/api/schedule/list", api_list_schedule)

app.router.add_post("/api/send", api_send)
app.router.add_get("/api/stats", api_stats)

app.router.add_get("/admin", admin_page)

# ===== START =====
async def start_all(app):
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(worker())
    asyncio.create_task(safe_scheduler())

app.on_startup.append(start_all)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
