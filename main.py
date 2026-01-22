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
OWNER_ID_RAW = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW and OWNER_ID_RAW.isdigit() else None

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

MAIN_MENU = ReplyKeyboardMarkup(
    [["🧮 Máy tính", "📄 Xem bill"], ["❌ Đóng"]],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [["🔢 Nhập giao dịch", "💸 Phí %"], ["⬅️ Quay lại"]],
    resize_keyboard=True
)

DATA = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Bill sẵn sàng", reply_markup=MAIN_MENU)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    if text == "🧮 Máy tính":
        DATA[uid] = {"rows": [], "fee": 0}
        await update.message.reply_text("Nhập: số / tỷ giá", reply_markup=CALC_MENU)

    elif text == "💸 Phí %":
        await update.message.reply_text("Nhập phí %")

    elif text == "📄 Xem bill":
        await show_bill(update, context)

    elif text == "⬅️ Quay lại":
        await update.message.reply_text("Menu chính", reply_markup=MAIN_MENU)

    elif uid in DATA:
        await handle_input(update, context)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    if text.replace(".", "").isdigit():
        DATA[uid]["fee"] = float(text)
        await update.message.reply_text(f"Đã set phí {text}%")
        return

    try:
        money, rate = text.split("/")
        usdt = float(money) / float(rate)
        DATA[uid]["rows"].append(usdt)
        await update.message.reply_text(f"Đã thêm {round(usdt,2)} USDT")
    except:
        await update.message.reply_text("Sai định dạng")

async def show_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    d = DATA.get(uid)

    if not d or not d["rows"]:
        await update.message.reply_text("Chưa có dữ liệu")
        return

    total = sum(d["rows"])
    fee = d["fee"]
    fee_value = total * fee / 100
    balance = total - fee_value

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    msg = [
        "HÓA ĐƠN",
        f"Thời gian: {now}",
        ""
    ]

    for i, v in enumerate(d["rows"], 1):
        msg.append(f"Giao dịch {i}: {round(v,2)} USDT")

    if fee:
        msg.append(f"Phí: {fee}% ({round(fee_value,2)} USDT)")

    msg += [
        "----------------",
        f"Tổng: {round(total,2)} USDT",
        f"Số dư: {round(balance,2)} USDT"
    ]

    await update.message.reply_text("\n".join(msg))

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
