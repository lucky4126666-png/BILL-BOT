import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

# ===== MENUS =====
MAIN_MENU = ReplyKeyboardMarkup(
    [["🧮 Máy tính", "📄 Xem bill"], ["❌ Đóng"]],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [["💸 Phí %"], ["⬅️ Quay lại"]],
    resize_keyboard=True
)

# ===== DATA =====
DATA = {}  # {user_id: {"rows": [], "fee": float}}

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot Bill đã sẵn sàng\nChọn chức năng:",
        reply_markup=MAIN_MENU
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    uid = update.message.from_user.id
    text = update.message.text.strip()

    if text == "🧮 Máy tính":
        DATA[uid] = {"rows": [], "fee": 0.0}
        await update.message.reply_text(
            "👉 Nhập giao dịch theo dạng:\n`SỐ / TỶ_GIÁ`\nVD: `1000000/25000`",
            reply_markup=CALC_MENU
        )

    elif text == "💸 Phí %":
        await update.message.reply_text("Nhập phí %, ví dụ: 1.5")

    elif text == "📄 Xem bill":
        await show_bill(update)

    elif text == "⬅️ Quay lại":
        await update.message.reply_text("Menu chính", reply_markup=MAIN_MENU)

    elif text == "❌ Đóng":
        DATA.pop(uid, None)
        await update.message.reply_text("Đã đóng phiên", reply_markup=MAIN_MENU)

    elif uid in DATA:
        await handle_input(update, uid, text)

async def handle_input(update: Update, uid: int, text: str):
    # nhập phí %
    if text.replace(".", "", 1).isdigit():
        DATA[uid]["fee"] = float(text)
        await update.message.reply_text(f"✅ Đã set phí {text}%")
        return

    # nhập giao dịch
    try:
        money, rate = text.split("/")
        usdt = float(money) / float(rate)
        DATA[uid]["rows"].append(usdt)
        await update.message.reply_text(f"➕ Thêm {usdt:.2f} USDT")
    except:
        await update.message.reply_text("❌ Sai định dạng. VD: 1000000/25000")

async def show_bill(update: Update):
    uid = update.message.from_user.id
    d = DATA.get(uid)

    if not d or not d["rows"]:
        await update.message.reply_text("❌ Chưa có dữ liệu")
        return

    total = sum(d["rows"])
    fee = d["fee"]
    fee_value = total * fee / 100
    balance = total - fee_value

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    msg = [
        "🧾 HÓA ĐƠN",
        f"⏰ {now}",
        ""
    ]

    for i, v in enumerate(d["rows"], 1):
        msg.append(f"{i}. {v:.2f} USDT")

    if fee > 0:
        msg.append(f"💸 Phí: {fee}% = {fee_value:.2f} USDT")

    msg += [
        "----------------",
        f"🔢 Tổng: {total:.2f} USDT",
        f"💰 Số dư: {balance:.2f} USDT"
    ]

    await update.message.reply_text("\n".join(msg))

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("✅ BOT BILL RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
