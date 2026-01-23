import os
from datetime import datetime, timezone, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "7993054192:AAEMYvFa_WG-_XuT4RkeW_qUNtVO-P-vy_c"
SUPER_ADMINS = {8572604188}   # 👈 ID CHỦ BOT
GROUP_ADMINS = {}            # admin theo group
groups = {}

# ================= TIME =================
def tz_vn():
    return timezone(timedelta(hours=7))

def today():
    return datetime.now(tz_vn()).strftime("%d/%m/%Y")

def now_time():
    return datetime.now(tz_vn()).strftime("%H:%M")

# ================= PERMISSION =================
def is_admin(uid, gid):
    return uid in SUPER_ADMINS or uid in GROUP_ADMINS.get(gid, set())

# ================= TEXT =================
MAIN_MENU_TEXT = (
    "━━━━━━━━━━━━━━━━━━\n"
    "🐉  TIANLONG BOT\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "📌 MENU CHÍNH"
)

ADMIN_MENU_TEXT = (
    "━━━━━━━━━━━━━━━━━━\n"
    "👑 ADMIN MENU\n"
    "━━━━━━━━━━━━━━━━━━"
)

# ================= KEYBOARD =================
def main_menu_kb(is_admin=True):
    btn = [
        [InlineKeyboardButton("📂 Quản lý nhóm", callback_data="group")],
        [InlineKeyboardButton("🧮 Máy tính", callback_data="calc")]
    ]
    if is_admin:
        btn.append([InlineKeyboardButton("👑 Admin", callback_data="admin")])
    btn.append([InlineKeyboardButton("❌ Đóng", callback_data="close")])
    return InlineKeyboardMarkup(btn)

def admin_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Thêm Admin", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Xóa Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 Danh sách Admin", callback_data="list_admin")],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data="back")]
    ])

CALC_MENU = ReplyKeyboardMarkup(
    [
        ["🔢 Tỷ giá", "💸 Phí %"],
        ["VN | 🇻🇳", "CN | 🇨🇳"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

# ================= STATE =================
def reset_state(ctx):
    ctx.user_data.pop("set_rate", None)
    ctx.user_data.pop("set_fee", None)

# ================= BILL (GIỮ NGUYÊN) =================
def render_bill(name, g):
    total_in = sum(i["usdt"] for i in g["inputs"])
    total_out = sum(o["usdt"] for o in g["outputs"])
    total = total_in - total_out

    if g["lang"] == "CN":
        lines = [
            f"🧾 账单 | {today()}",
            f"👤 创建者: {name}",
            "⸻",
            f"收入 ({len(g['inputs'])})"
        ]
        for i in g["inputs"]:
            lines.append(f"{i['time']} | {i['vnd']:,.0f} / {g['rate']} = {i['usdt']:,.2f} USDT")

        lines += ["⸻", f"支出 ({len(g['outputs'])})"]
        for o in g["outputs"]:
            lines.append(f"-{o['usdt']:,.2f} USDT")

        lines += [
            "⸻",
            f"+ 收入 : {total_in:,.2f} USDT",
            f"- 支出 : {total_out:,.2f} USDT",
            f"💰 总计 : <b>{total:,.2f} USDT</b>"
        ]
        return "\n".join(lines)

    lines = [
        f"🧾 HÓA ĐƠN | {today()}",
        f"👤 Người tạo: {name}",
        "⸻",
        f"Nhập ({len(g['inputs'])})"
    ]
    for i in g["inputs"]:
        lines.append(f"{i['time']} | {i['vnd']:,.0f} / {g['rate']} = {i['usdt']:,.2f} USDT")

    lines += ["⸻", f"Xuất ({len(g['outputs'])})"]
    for o in g["outputs"]:
        lines.append(f"-{o['usdt']:,.2f} USDT")

    lines += [
        "⸻",
        f"+ Nhập : {total_in:,.2f} USDT",
        f"- Xuất : {total_out:,.2f} USDT",
        f"💰 Tổng cộng : <b>{total:,.2f} USDT</b>"
    ]
    return "\n".join(lines)

# ================= /START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    gid = update.effective_chat.id

    if not is_admin(uid, gid):
        return

    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_kb(True)
    )

# ================= CALLBACK =================

  async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    gid = q.message.chat.id
    data = q.data

    if not is_admin(uid, gid):
        return

    if data == "admin_menu":
        await q.edit_message_text("👑 ADMIN MENU", reply_markup=admin_menu_keyboard())

    elif data == "add_admin":
        if uid != OWNER_ID:
            await q.edit_message_text("❌ Chỉ chủ bot mới được thêm admin")
            return
        context.user_data["await_add_admin"] = True
        await q.message.reply_text("📥 Nhập USER ID cần thêm admin:")

    elif data == "remove_admin":
        if uid != OWNER_ID:
            await q.edit_message_text("❌ Chỉ chủ bot mới được xóa admin")
            return
        context.user_data["await_remove_admin"] = True
        await q.message.reply_text("📥 Nhập USER ID cần xóa admin:")

    elif data == "list_admin":
        admins = ADMINS.union(GROUP_ADMINS.get(gid, set()))
        text = "📋 ADMIN LIST\n\n" + "\n".join(str(a) for a in admins)
        await q.edit_message_text(text, reply_markup=admin_menu_keyboard())

    elif data == "back_main":
        await q.edit_message_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())

    elif data == "calc":
        await q.message.reply_text("🧮 Máy tính", reply_markup=CALC_MENU)

    elif data == "close":
        await q.message.delete()

# ================= MESSAGE =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    uid = update.effective_user.id
    gid = update.effective_chat.id
    name = update.effective_user.first_name

    if not is_admin(uid, gid):
        return

    # ===== ADD ADMIN =====
    if context.user_data.get("await_add_admin"):
        try:
            aid = int(msg)
            ADMINS.add(aid)
            context.user_data.clear()
            await update.message.reply_text("✅ Đã thêm admin")
        except:
            await update.message.reply_text("❌ ID không hợp lệ")
        return

    if context.user_data.get("await_remove_admin"):
        try:
            rid = int(msg)
            ADMINS.discard(rid)
            context.user_data.clear()
            await update.message.reply_text("✅ Đã xóa admin")
        except:
            await update.message.reply_text("❌ ID không hợp lệ")
        return
# ================= MESSAGE =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    uid = update.effective_user.id
    gid = update.effective_chat.id
    name = update.effective_user.first_name

    if not is_admin(uid, gid):
        return

    if gid not in groups:
        groups[gid] = {
            "rate": 1.0,
            "fee": 0.0,
            "lang": "VN",
            "inputs": [],
            "outputs": []
        }

    g = groups[gid]

    if msg == "⬅️ Quay lại":
        reset_state(context)
        await update.message.reply_text("Menu chính", reply_markup=main_menu_kb(True))
        return

    if msg.startswith("VN"):
        g["lang"] = "VN"
        await update.message.reply_text("🇻🇳 Đã chuyển Tiếng Việt")
        return

    if msg.startswith("CN"):
        g["lang"] = "CN"
        await update.message.reply_text("🇨🇳 已切换中文")
        return

    if msg == "🔢 Tỷ giá":
        reset_state(context)
        context.user_data["set_rate"] = True
        await update.message.reply_text("Nhập tỷ giá:")
        return

    if context.user_data.get("set_rate"):
        try:
            g["rate"] = float(msg)
            reset_state(context)
            await update.message.reply_text("✅ Đã đặt tỷ giá")
        except:
            await update.message.reply_text("❌ Tỷ giá không hợp lệ")
        return

    if msg == "💸 Phí %":
        reset_state(context)
        context.user_data["set_fee"] = True
        await update.message.reply_text("Nhập % phí:")
        return

    if context.user_data.get("set_fee"):
        try:
            g["fee"] = float(msg)
            reset_state(context)
            await update.message.reply_text("✅ Đã đặt phí")
        except:
            await update.message.reply_text("❌ Phí không hợp lệ")
        return

    if msg in ["+0", "-0"]:
        g["inputs"].clear()
        g["outputs"].clear()
        await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        return

    if msg.startswith("+"):
        vnd = float(msg[1:])
        usdt = round(vnd / g["rate"], 2)
        g["inputs"].append({"time": now_time(), "vnd": vnd, "usdt": usdt})
        await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        return

    if msg.startswith("-"):
        usdt = float(msg[1:])
        g["outputs"].append({"usdt": round(usdt, 2)})
        await update.message.reply_text(render_bill(name, g), parse_mode="HTML")

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    print("🐉 TianLong Bot running…")
    app.run_polling()

if __name__ == "__main__":
    main()

