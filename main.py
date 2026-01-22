import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

groups = {}

# ================= HELPERS =================
async def is_admin_or_owner(update, context):
    user = update.effective_user
    chat = update.effective_chat

    if user.id == OWNER_ID:
        return True

    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ("administrator", "creator")

def get_group(chat_id):
    if chat_id not in groups:
        groups[chat_id] = {
            "rate": 1.0,
            "fee": 0.0,
            "lang": "VN",
            "bill_lines": [],
            "total_in": 0.0,
            "total_out": 0.0,
        }
    return groups[chat_id]

def fmt(n):
    return int(n) if n == int(n) else round(n, 2)

def build_bill(data):
    fee_value = data["total_in"] * data["fee"] / 100
    balance = data["total_in"] - fee_value - data["total_out"]
    today = datetime.now().strftime("%d/%m/%Y")

    if data["lang"] == "CN":
        text = "账单\n\n"
        text += "操作人: TianLong\n"
        text += f"时间: {today}\n\n"
    else:
        text = "HÓA ĐƠN\n\n"
        text += "Người tạo: TianLong\n"
        text += f"Thời gian: {today}\n\n"

    for line in data["bill_lines"]:
        text += line + "\n"

    if data["fee"] > 0:
        if data["lang"] == "CN":
            text += f"\n手续费: {fmt(data['fee'])}% ({fmt(fee_value)} USDT)\n"
        else:
            text += f"\nPhí: {fmt(data['fee'])}% ({fmt(fee_value)} USDT)\n"

    text += "——————————————————-\n"

    if data["lang"] == "CN":
        text += f"总收入: {fmt(data['total_in'])} USDT\n"
        text += f"总支出: {fmt(data['total_out'])} USDT\n"
        text += f"余额: **{fmt(balance)} USDT**"
    else:
        text += f"Tổng thu: {fmt(data['total_in'])} USDT\n"
        text += f"Tổng chi: {fmt(data['total_out'])} USDT\n"
        text += f"Số dư: **{fmt(balance)} USDT**"

    return text

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    if not await is_admin_or_owner(update, context):
        return

    kb = [
        [InlineKeyboardButton("📜 Quản lý nhóm", callback_data="manage")],
        [InlineKeyboardButton("🛡 Quyền hạn", callback_data="role")],
        [InlineKeyboardButton("💻 Máy tính", callback_data="calc")],
        [InlineKeyboardButton("💰 Ví USDT", callback_data="wallet")],
        [InlineKeyboardButton("❌ Đóng", callback_data="close")],
    ]
    await update.message.reply_text("MENU", reply_markup=InlineKeyboardMarkup(kb))

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not await is_admin_or_owner(update, context):
        return

    chat_id = q.message.chat.id
    data = get_group(chat_id)

    if q.data == "calc":
        kb = [
            [InlineKeyboardButton("🔢 Tỷ giá", callback_data="rate")],
            [InlineKeyboardButton("💸 Phí", callback_data="fee")],
            [InlineKeyboardButton("🌐 Ngôn ngữ bill", callback_data="lang")],
            [InlineKeyboardButton("❌ Đóng", callback_data="close")],
        ]
        await q.edit_message_text("💻 Máy tính", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "rate":
        context.user_data["await_rate"] = True
        await q.edit_message_text("🔢 Nhập tỷ giá:")

    elif q.data == "fee":
        context.user_data["await_fee"] = True
        await q.edit_message_text("💸 Nhập phí (%):")

    elif q.data == "lang":
        kb = [
            [InlineKeyboardButton("VN", callback_data="lang_vn")],
            [InlineKeyboardButton("(CN)", callback_data="lang_cn")],
            [InlineKeyboardButton("⬅️ Quay lại", callback_data="calc")],
        ]
        await q.edit_message_text("🌐 Ngôn ngữ bill", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "lang_vn":
        data["lang"] = "VN"
        await q.edit_message_text("✅ Đã đổi ngôn ngữ bill: VN")

    elif q.data == "lang_cn":
        data["lang"] = "CN"
        await q.edit_message_text("✅ 已切换账单语言: 中文")

    elif q.data == "close":
        await q.delete_message()

# ================= MESSAGE =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    if not await is_admin_or_owner(update, context):
        return

    chat_id = update.effective_chat.id
    data = get_group(chat_id)
    text = update.message.text.strip()

    # nhập tỷ giá
    if context.user_data.get("await_rate"):
        data["rate"] = float(text)
        context.user_data["await_rate"] = False
        await update.message.reply_text(f"✅ Đã đặt tỷ giá: {text}")
        return

    # nhập phí
    if context.user_data.get("await_fee"):
        data["fee"] = float(text)
        context.user_data["await_fee"] = False
        await update.message.reply_text(f"✅ Đã đặt phí: {text}%")
        return

    # + / -
    if text.startswith("+") or text.startswith("-"):
        value = float(text)

        # +0 / -0 → reset số nhưng vẫn in bill
        if value == 0:
            data["bill_lines"].clear()
            data["total_in"] = 0.0
            data["total_out"] = 0.0
            data["fee"] = 0.0
            await update.message.reply_text(build_bill(data), parse_mode="Markdown")
            return

        now = datetime.now().strftime("%H:%M")

        if value > 0:
            usdt = value / data["rate"]
            data["total_in"] += usdt
            data["bill_lines"].append(
                f"{now}  {fmt(value)} / {data['rate']} = {fmt(usdt)} USDT"
            )
        else:
            data["total_out"] += abs(value)

        await update.message.reply_text(build_bill(data), parse_mode="Markdown")

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
app.run_polling()
