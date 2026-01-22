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
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

# ===== MENUS =====
MAIN_MENU = ReplyKeyboardMarkup(
    [["🧮 Máy tính", "📄 Xem bill"], ["❌ Đóng"]],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [["💸 Phí %", "⬅️ Quay lại"]],
    resize_keyboard=True
)

# ===== DATA =====
DATA = {}

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot quản lý bill đã sẵn sàng",
        reply_markup=MAIN_MENU
    )

# ===== HANDLER =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    uid = update.message.from_user.id
    text = update.message.text.strip()

    if text == "🧮 Máy tính":
        DATA[uid] = {"rows": [], "fee": 0}
        await update.message.reply_text(
            "📥 Nhập giao dịch theo dạng:\n`SỐ / TỶ GIÁ`\nVí dụ: `1000000/25000`",
            reply_markup=CALC_MENU
        )

    elif text == "💸 Phí %":
        await update.message.reply_text("Nhập % phí (ví dụ: 2.5)")

    elif text == "📄 Xem bill":
        await show_bill(update)

    elif text == "⬅️ Quay lại":
        await update.message.reply_text("Menu chính", reply_markup=MAIN_MENU)

    elif uid in DATA:
        await handle_input(update)

# ===== INPUT =====
async def handle_input(update: Update):
    uid = update.message.from_user.id
    text = update.message.text.replace(" ", "")

    # Set fee
    if text.replace(".", "", 1).isdigit():
        DATA[uid]["fee"] = float(text)
        await update.message.reply_text(f"✅ Đã đặt phí: {text}%")
        return

    # Add transaction
    try:
        money, rate = text.split("/")
        usdt = float(money) / float(rate)
        DATA[uid]["rows"].append(usdt)
        await update.message.reply_text(f"➕ Thêm: {round(usdt, 2)} USDT")
    except:
        await update.message.reply_text("❌ Sai định dạng. Ví dụ: 1000000/25000")

# ===== BILL =====
async def show_bill(update: Update):
    uid = update.message.from_user.id
    d = DATA.get(uid)

    if not d or not d["rows"]:
        await update.message.reply_text("⚠️ Chưa có dữ liệu")
        return

    total = sum(d["rows"])
    fee = d["fee"]
    fee_value = total * fee / 100
    balance = total - fee_value

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "🧾 HÓA ĐƠN",
        f"⏰ {now}",
        ""
    ]

    for i, v in enumerate(d["rows"], 1):
        lines.append(f"Giao dịch {i}: {round(v,2)} USDT")

    if fee > 0:
        lines.append(f"Phí: {fee}% = {round(fee_value,2)} USDT")

    lines += [
        "----------------",
        f"Tổng: {round(total,2)} USDT",
        f"Số dư: {round(balance,2)} USDT"
    ]

    await update.message.reply_text("\n".join(lines))

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
