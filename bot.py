import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")

# --- товары ---
fruits = {
    "🍎 Яблоко красное": 130,
    "🍏 Яблоко зеленое": 150,
    "🍊 Грейпфрут": 160,
    "🥑 Авокадо": 450,
    "🍋 Лимон": 250,
    "🍈 Лайм": 420,
    "🍊 Мандарин мини": 130,
    "🍊 Мандарин турция": 220
}

vegetables = {
    "🥕 Морковь": 25,
    "🥔 Картофель": 25,
    "🥔 Картофель Мини": 100,
    "🧅 Лук репчатый": 25,
    "🧅 Лук красный": 50,
    "🥬 Капуста": 25,
    "🥬 Капуста красная": 90,
    "🥕 Свекла": 25,
    "🥒 Огурцы": 150,
    "🥒 Кабачки": 170,
    "🍆 Баклажаны": 220,
    "🎃 Тыква": 90,
    "🌿 Укроп": 230,
    "🌿 Петрушка": 230,
    "🌿 Тимьян": 1200,
    "🌿 Розмарин": 1200,
    "🌿 Мята": 1300,
    "🌿 Базилик": 1600,
    "🥬 Шпинат": 450,
    "🌿 Кинза": 350,
    "🧅 Лук зеленый": 350,
    "🥬 Щавель": 450,
    "🥬 Руккола": 600,
    "🧄 Чеснок": 180,
    "🥕 Имбирь": 260,
    "🌶 Перец": 240,
    "🍄 Шампиньоны": 270
}

orders = {}
user_item_temp = {}

ENTER_WEIGHT, ENTER_ADDRESS = range(2)

# --- клавиатуры ---
def build_category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍎 Фрукты", callback_data="fruits")],
        [InlineKeyboardButton("🥕 Овощи и зелень", callback_data="vegetables")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="view_order")]
    ])

def build_cart_keyboard(user_id):
    user_order = orders.get(user_id, {})
    keyboard = []
    for item, qty in user_order.items():
        price = fruits.get(item) or vegetables.get(item)
        keyboard.append([
            InlineKeyboardButton(f"{item} −", callback_data=f"dec_{item}"),
            InlineKeyboardButton(f"{qty:.2f} кг x {price} ₽/кг", callback_data="none"),
            InlineKeyboardButton(f"{item} +", callback_data=f"inc_{item}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{item}")
        ])
    if user_order:
        total = sum((fruits.get(i, vegetables.get(i)) * q) for i, q in user_order.items())
        keyboard.append([InlineKeyboardButton(f"💳 Оплатить (Итого: {total:.2f} ₽)", callback_data="pay")])
    keyboard.append([InlineKeyboardButton("🏠 Меню", callback_data="start")])
    return InlineKeyboardMarkup(keyboard)

def build_weight_keyboard(item):
    keyboard = []
    for w in [0.5, 1, 2, 5, 10]:
        keyboard.append([InlineKeyboardButton(f"{w} кг", callback_data=f"setweight_{w}_{item}")])
    keyboard.append([InlineKeyboardButton("✏️ Ввести свой вес", callback_data=f"customweight_{item}")])
    keyboard.append([InlineKeyboardButton("🏠 Меню", callback_data="start")])
    return InlineKeyboardMarkup(keyboard)

# --- обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Добро пожаловать в Шеф Маркет! Выберите категорию:", reply_markup=build_category_keyboard())
    else:
        await update.callback_query.edit_message_text("Выберите категорию:", reply_markup=build_category_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data
    if user_id not in orders:
        orders[user_id] = {}
    def get_price(item):
        return fruits.get(item) or vegetables.get(item)
    # --- обработка кнопок ---
    if data == "fruits":
        keyboard = [[InlineKeyboardButton(f"{i} (+)", callback_data=f"chooseweight_{i}")] for i in fruits.keys()]
        keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="start")])
        await query.edit_message_text("Выберите фрукт:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "vegetables":
        keyboard = [[InlineKeyboardButton(f"{i} (+)", callback_data=f"chooseweight_{i}")] for i in vegetables.keys()]
        keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="start")])
        await query.edit_message_text("Выберите овощ или зелень:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("chooseweight_"):
        item = data[13:]
        user_item_temp[user_id] = item
        await query.edit_message_text(f"Выберите вес для {item}:", reply_markup=build_weight_keyboard(item))
    elif data.startswith("setweight_"):
        parts = data.split("_")
        weight = float(parts[1])
        item = "_".join(parts[2:])
        orders[user_id][item] = orders[user_id].get(item, 0) + weight
        await query.edit_message_text(f"{item} добавлен в корзину: {weight:.2f} кг", reply_markup=build_cart_keyboard(user_id))
    elif data.startswith("customweight_"):
        item = data[13:]
        user_item_temp[user_id] = item
        await query.edit_message_text(f"Введите вес для {item} вручную (0–100 кг):")
        return ENTER_WEIGHT
    elif data.startswith("inc_"):
        item = data[4:]
        orders[user_id][item] += 0.5
        await query.edit_message_text("Корзина обновлена:", reply_markup=build_cart_keyboard(user_id))
    elif data.startswith("dec_"):
        item = data[4:]
        if orders[user_id][item] > 0.5:
            orders[user_id][item] -= 0.5
        else:
            del orders[user_id][item]
        await query.edit_message_text("Корзина обновлена:", reply_markup=build_cart_keyboard(user_id))
    elif data.startswith("del_"):
        item = data[4:]
        orders[user_id].pop(item, None)
        await query.edit_message_text("Корзина обновлена:", reply_markup=build_cart_keyboard(user_id))
    elif data == "view_order":
        await query.edit_message_text("Ваша корзина:", reply_markup=build_cart_keyboard(user_id))
    elif data == "pay":
        user_order = orders.get(user_id, {})
        if not user_order:
            await query.edit_message_text("Ваша корзина пуста.", reply_markup=build_category_keyboard())
            return
        await query.edit_message_text("Пожалуйста, введите адрес доставки в пределах Красноярска:")
        return ENTER_ADDRESS
    elif data == "start":
        await start(update, context)

async def enter_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_item_temp:
        await update.message.reply_text("Ошибка. Пожалуйста, выберите товар заново.")
        return ConversationHandler.END
    item = user_item_temp[user_id]
    try:
        weight = float(update.message.text.replace(",", "."))
        if not (0 < weight <= 100):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите корректный вес от 0 до 100 кг.")
        return ENTER_WEIGHT
    orders[user_id][item] = orders[user_id].get(item, 0) + weight
    await update.message.reply_text(f"{item} добавлен в корзину: {weight:.2f} кг", reply_markup=build_cart_keyboard(user_id))
    del user_item_temp[user_id]
    return ConversationHandler.END

async def enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    address = update.message.text.strip()
    if "красноярск" not in address.lower():
        await update.message.reply_text("Адрес должен быть в пределах города Красноярска. Попробуйте снова:")
        return ENTER_ADDRESS
    user_order = orders.get(user_id, {})
    order_text = "\n".join([f"{item} — {qty:.2f} кг" for item, qty in user_order.items()])
    # отправка админу
    await context.bot.send_message(chat_id=ADMIN_USERNAME, text=f"📦 Новый заказ от @{update.message.from_user.username or user_id}:\nАдрес: {address}\n{order_text}")
    orders[user_id] = {}
    await update.message.reply_text("✅ Ваш заказ принят! Спасибо!")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern="customweight_")],
        states={
            ENTER_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_weight)],
            ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_address)]
        },
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()
