import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Шаги состояний
NAME, AMOUNT, ACCOUNT, CURRENCY, CATEGORY, OTHER_ACCOUNT, OTHER_CATEGORY = range(7)

# Клавиатуры

def build_account_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Revolut", callback_data="Revolut")],
        [InlineKeyboardButton("BCC", callback_data="BCC")],
        [InlineKeyboardButton("Alta", callback_data="Alta")],
        [InlineKeyboardButton("Тиньков", callback_data="Тиньков")],
        [InlineKeyboardButton("Другое", callback_data="other_account")],
    ])

def build_currency_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Euro", callback_data="Euro"), InlineKeyboardButton("RSD", callback_data="RSD")],
        [InlineKeyboardButton("pounds", callback_data="pounds"), InlineKeyboardButton("руб", callback_data="руб")],
        [InlineKeyboardButton("amer", callback_data="amer"), InlineKeyboardButton("tenge", callback_data="tenge")],
    ])

def build_category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍲 Еда", callback_data="🍲 Еда"), InlineKeyboardButton("🥐☕️ Кофе", callback_data="🥐☕️ Кофе")],
        [InlineKeyboardButton("🛒 Grocery", callback_data="🛒 Grocery"), InlineKeyboardButton("🧺 Бытовые", callback_data="🧺 Бытовые")],
        [InlineKeyboardButton("🚕 Транспорт", callback_data="🚕 Транспорт"), InlineKeyboardButton("🏥 Здоровье", callback_data="🏥 Здоровье")],
        [InlineKeyboardButton("✈️ Путешествия", callback_data="✈️ Путешествия"), InlineKeyboardButton("💃 Развлечения", callback_data="💃 Развлечения")],
        [InlineKeyboardButton("🚰 Коммуналка", callback_data="🚰 Коммуналка"), InlineKeyboardButton("🎁 Подарки", callback_data="🎁 Подарки")],
        [InlineKeyboardButton("💔 Благотворительные", callback_data="💔 Благотворительные"), InlineKeyboardButton("🏠 Аренда", callback_data="🏠 Аренда")],
        [InlineKeyboardButton("📱 Подписки", callback_data="📱 Подписки"), InlineKeyboardButton("💄 Beauty", callback_data="💄 Beauty")],
        [InlineKeyboardButton("Другое", callback_data="other_category")],
    ])

# Хендлеры

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s started conversation", update.effective_user.id)
    await update.message.reply_text("Привет! Введи название расхода:")
    return NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите сумму расхода:")
    return AMOUNT

async def ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['amount'] = float(update.message.text)
        await update.message.reply_text("Выберите счёт:", reply_markup=build_account_keyboard())
        return ACCOUNT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную сумму.")
        return AMOUNT

async def ask_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'other_account':
        await query.edit_message_text("Введите другой счёт:")
        return OTHER_ACCOUNT
    context.user_data['account'] = query.data
    await query.edit_message_text("Выберите валюту расхода:", reply_markup=build_currency_keyboard())
    return CURRENCY

async def handle_other_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['account'] = update.message.text
    await update.message.reply_text("Выберите валюту расхода:", reply_markup=build_currency_keyboard())
    return CURRENCY

async def ask_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['currency'] = query.data
    await query.edit_message_text("Выберите категорию:", reply_markup=build_category_keyboard())
    return CATEGORY

async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'other_category':
        await query.edit_message_text("Введите другую категорию:")
        return OTHER_CATEGORY
    context.user_data['category'] = query.data
    return await send_data(update, context)

async def handle_other_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['category'] = update.message.text
    return await send_data(update, context)

async def send_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    payload = {
        'Название расхода': context.user_data['name'],
        'Сумма расхода': context.user_data['amount'],
        'Счёт': context.user_data['account'],
        'валюта расхода': context.user_data['currency'],
        'Категория': context.user_data['category']
    }
    logger.info(f"Отправка данных: %s", payload)
    try:
        response = requests.post(
            'https://script.google.com/macros/s/AKfycbyEMTwPPvCqg4YjhjbikdIvwBo2TmePEBPYeqfBShQ9-XYlaOeuqro1bui2xjB0OfxJSg/exec',
            data=payload
        )
        logger.info(f"Response status: %s, text: %s", response.status_code, response.text)
        if response.ok:
            await update.effective_message.reply_text("Данные успешно отправлены!")
        else:
            await update.effective_message.reply_text("Ошибка при отправке данных.")
    except Exception as e:
        logger.error("Ошибка при запросе: %s", e)
        await update.effective_message.reply_text(f"Ошибка запроса: {e}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Точка входа

def main():
    token = os.environ.get("TELEGRAM_TOKEN") or "7826192630:AAGyqFR3BlRE_-Wi8lUtC7w8X46dWM07hw0"
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_amount)],
            ACCOUNT: [CallbackQueryHandler(ask_account)],
            OTHER_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_account)],
            CURRENCY: [CallbackQueryHandler(ask_currency)],
            CATEGORY: [CallbackQueryHandler(ask_category)],
            OTHER_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

