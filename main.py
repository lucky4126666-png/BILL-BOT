import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN or not OWNER_ID:
    raise RuntimeError("Thiếu BOT_TOKEN hoặc OWNER_ID")

# ===== MENU =====
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📜 Quản lý nhóm"],
        ["🧮 Máy tính"],
        ["❌ Đóng"]
    ],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [
        ["🔢 Tỷ giá", "💸 Phí %"],
        ["📄 Xem bill"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

# ===== DATA =====
BILL = {
    "rate": None,
    "fee": None,
    "in": [],
    "out": []
}

# ===== UTILS =====
def is_admin(update: Update) -> bool:
    uid = update.effective_user.id
    if uid == OWNER_ID:
        return True
    member = update.effective_chat.get_member(uid)
    return member.status in ("administrator", "creator")

def fmt(n):
    return int(n) if n == int(n) else round(n, 2)

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text(
        "🤖 Bot quản lý & bill sẵn sàng",
        reply_markup=MAIN_MENU
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    text = update.message.text.strip()

    # ===== MENU =====
    if text == "📜 Quản lý nhóm":
        await update.message.reply_text(
            "📜 Quản lý nhóm\n• Nội quy\n• Quyền hạn\n• Thông tin admin",
            reply_markup=MAIN_MENU
        )

    elif text == "🧮 Máy tính":
        await update.message.reply_text(
            "🧮 Máy tính bill",
            reply_markup=CALC_MENU
        )

    elif text == "🔢 Tỷ giá":
        context.user_data["wait_rate"] = True
        await update.message.reply_text("Nhập tỷ giá")

    elif text == "💸 Phí %":
        context.user_data["wait_fee"] = True
        await update.message.reply_text("Nhập phí % (vd: 6)")

    elif text == "📄 Xem bill":
        await send_bill(update)

    elif text == "⬅️ Quay lại":
        await update.message.reply_text("Menu chính", reply_markup=MAIN_MENU)

    elif text == "❌ Đóng":
        await update.message.delete()

    # ===== INPUT =====
    else:
        await handle_input(update, context)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(" ", "")

    # ===== SET RATE =====
    if context.user_data.pop("wait_rate", False):
        BILL["rate"] = float(text)
        await update.message.reply_text(f"✅ Đã đặt tỷ giá {text}")
        return

    # ===== SET FEE =====
    if context.user_data.pop("wait_fee", False):
        BILL["fee"] = float(text)
        await update.message.reply_text(f"✅ Đã đặt phí {text}%")
        return

    # ===== RESET =====
    if text in ("+0", "-0"):
        BILL["in"].clear()
        BILL["out"].clear()
        await send_bill(update)
        return

    # ===== + / - =====
    if text.startswith("+"):
        BILL["in"].append(float(text[1:]))
        await send_bill(update)

    elif text.startswith("-"):
        BILL["out"].append(float(text[1:]))
        await send_bill(update)

async def send_bill(update: Update):
    rate = BILL["rate"]
    fee = BILL["fee"]

    total_in = sum(BILL["in"])
    total_out = sum(BILL["out"])

    fee_value = (total_in * fee / 100) if fee else 0
    balance = total_in - total_out - fee_value

    now = datetime.now()
    lines = []

    for v in BILL["in"]:
        if rate:
            lines.append(f"{fmt(v)} / {rate} = {fmt(v / rate)} USDT")
        else:
            lines.append(f"+ {fmt(v)}")

    msg = [
        "HÓA ĐƠN",
        f"Người tạo: {update.effective_user.first_name}",
        f"Thời gian: {now.strftime('%d/%m/%Y %H:%M')}",
        "",
        *lines,
        ""
    ]

    if fee:
        msg.append(f"Phí: {fee}% ({fmt(fee_value)} USDT)")

    msg += [
        "—————————————",
        f"Tổng thu: {fmt(total_in)} USDT",
        f"Tổng chi: {fmt(total_out)} USDT",
        f"Số dư: **{fmt(balance)} USDT**"
    ]

    await update.message.reply_text("\n".join(msg), parse_mode="Markdown")

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
