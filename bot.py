from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)

TOKEN = "8505519433:AAHP8M9RODy9zpLJRz6Bb9xMjrXKyRHjvdE"
ADMIN_IDS = [8249302541]

# ---------- INFO ----------
info_text = """
🤖 Добро пожаловать в официальный донат-бот магазина!

💎 Здесь вы можете:
- Приобрести игровую валюту
- Оплатить и отправить чек
- Получить донат после проверки администратором
"""

# ---------- SHOP ----------
shop_data = {
    "Алмазы": [
        {"name": "💎 100 алмазов", "price": "100₽"},
        {"name": "💎 300 алмазов", "price": "250₽"},
        {"name": "💎 500 алмазов", "price": "400₽"},
    ],
    "Эсэ": [
        {"name": "⭐ 10 эсэ", "price": "50₽"},
        {"name": "⭐ 25 эсэ", "price": "120₽"},
    ]
}

user_state = {}

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=name)] for name in shop_data]
    await update.message.reply_text(
        "Выберите раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(info_text)

# ---------- SECTION ----------
async def section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id] = {
        "section": query.data,
        "package": None,
        "paid": False,
        "awaiting_id": False
    }

    keyboard = [
        [InlineKeyboardButton(
            f"{pkg['name']} — {pkg['price']}",
            callback_data=f"pkg_{i}"
        )]
        for i, pkg in enumerate(shop_data[query.data])
    ]

    await query.edit_message_text(
        "Выберите пакет:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- PACKAGE ----------
async def package_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[1])
    uid = query.from_user.id
    package = shop_data[user_state[uid]["section"]][idx]
    user_state[uid]["package"] = package

    await query.edit_message_text(
        f"{package['name']}\nЦена: {package['price']}\n\n"
        "💳 Оплатите и нажмите «Я оплатил»",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data="paid")]
        ])
    )

# ---------- PAID ----------
async def paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id]["paid"] = True
    await query.edit_message_text("📸 Отправьте чек (фото или текст)")

# ---------- ID + NICK (ВАЖНО: ПЕРВЫМ) ----------
async def id_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    if uid not in user_state:
        return
    if not user_state[uid].get("awaiting_id"):
        return

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            admin_id,
            f"🎮 ДАННЫЕ ИГРОКА\n"
            f"@{update.message.from_user.username}\n"
            f"{update.message.text}"
        )

    await update.message.reply_text("✅ Данные переданы админу")
    user_state.pop(uid, None)

# ---------- CHECK ----------
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    if uid not in user_state:
        return
    if not user_state[uid]["paid"]:
        return
    if user_state[uid]["awaiting_id"]:
        return

    package = user_state[uid]["package"]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm|{uid}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_decline|{uid}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=update.message.photo[-1].file_id,
                caption=f"🧾 ЧЕК\n@{update.message.from_user.username}\n"
                        f"{package['name']} — {package['price']}",
                reply_markup=keyboard
            )
        else:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🧾 ЧЕК\n@{update.message.from_user.username}\n"
                     f"{package['name']} — {package['price']}\n\n"
                     f"{update.message.text}",
                reply_markup=keyboard
            )

    await update.message.reply_text("✅ Чек отправлен администратору")

# ---------- ADMIN ----------
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid = query.data.split("|")
    uid = int(uid)

    if uid not in user_state:
        await query.edit_message_text("❌ Заявка устарела")
        return

    if action == "admin_confirm":
        user_state[uid]["awaiting_id"] = True
        await context.bot.send_message(
            uid,
            "🎮 Отправьте ID и Ник игрока одним сообщением"
        )
        await query.edit_message_text("✅ Подтверждено")
    else:
        await context.bot.send_message(uid, "❌ Оплата отклонена")
        user_state.pop(uid, None)
        await query.edit_message_text("❌ Отклонено")

# ---------- MAIN ----------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("info", info))
app.add_handler(CallbackQueryHandler(section_callback, pattern="^(Алмазы|Эсэ)$"))
app.add_handler(CallbackQueryHandler(package_callback, pattern="^pkg_"))
app.add_handler(CallbackQueryHandler(paid_callback, pattern="^paid$"))
app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

# ⚠️ ПОРЯДОК ВАЖЕН
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, id_message))
app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, check_message))

app.run_polling()