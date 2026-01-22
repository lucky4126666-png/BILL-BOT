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

# ====== ENV ======
BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID_RAW = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW and OWNER_ID_RAW.isdigit() else None

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN chưa được cấu hình")

# ====== MENU ======
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🧮 Máy tính", "📄 Xem bill"],
        ["❌ Đóng"]
    ],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [
        ["🔢 Tỷ giá", "💸 Phí %"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

# ====== DATA TEMP ======
USER_DATA = {}

# ====== HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot Bill đang hoạt động\nChọn chức năng:",
        reply_markup=MAIN_MENU
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.message.from_user.id

    if text == "🧮 Máy tính":
        USER_DATA[uid] = {"rows": [], "fee": 0}
        await update.message.reply_text(
            "📌 Nhập giao dịch theo dạng:\n`SỐ TIỀN / TỶ GIÁ`\nVí dụ: `300000 / 27.55`",
            reply_markup=CALC_MENU
        )

    elif text == "💸 Phí %":
        await update.message.reply_text("Nhập phí % (ví dụ: 6)")

    elif text == "🔢 Tỷ giá":
        await update.message.reply_text("Nhập giao dịch: `SỐ / TỶ GIÁ`")

    elif text == "📄 Xem bill":
        await show_bill(update, context)

    elif text == "⬅️ Quay lại":
        await update.message.reply_text("Quay lại menu chính", reply_markup=MAIN_MENU)

    elif text == "❌ Đóng":
        await update.message.reply_text("Đã đóng menu")

    else:
        await handle_input(update, context)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    if uid not in USER_DATA:
        return

    # PHÍ %
    if text.replace(".", "").isdigit():
        USER_DATA[uid]["fee"] = float(text)
        await update.message.reply_text(f"✅ Đã set phí {text}%")
        return

    # GIAO DỊCH
    try:
        money, rate = text.split("/")
        money = float(money.strip())
        rate = float(rate.strip())
        usdt = money / rate
        USER_DATA[uid]["rows"].append(usdt)

        await update.message.reply_text(
            f"✔ Đã thêm: {money} / {rate} = {round(usdt,2)} USDT"
        )
    except:
        await update.message.reply_text("❌ Sai định dạng. Ví dụ: 300000 / 27.55")

async def show_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    data = USER_DATA.get(uid)

    if not data or not data["rows"]:
        await update.message.reply_text("❌ Chưa có dữ liệu")
        return

    total = sum(data["rows"])
    fee_percent = data.get("fee", 0)
    fee_value = total * fee_percent / 100 if fee_percent else 0
    balance = total - fee_value

    now = datetime.now()
    bill = [
        "HÓA ĐƠN\n",
        f"Người tạo: {update.message.from_user.first_name}",
        f"Thời gian: {now.strftime('%d/%m/%Y %H:%M')}\n"
    ]

    for i, v in enumerate(data["rows"], 1):
        bill.append(f"Giao dịch {i}: {round(v,2)} USDT")

    if fee_percent:
        bill.append(f"\nPhí: {fee_percent}% ({round(fee_value,2)} USDT)")

    bill.extend([
        "—————————————",
        f"Tổng thu: {round(total,2)} USDT",
        f"Số dư: {round(balance,2)} USDT"
    ])

    await update.message.reply_text("\n".join(bill))

# ====== MAIN ======
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    print("🤖 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
