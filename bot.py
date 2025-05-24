import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
import requests

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Шаги состояния
NAME, AMOUNT, ACCOUNT, CURRENCY, CATEGORY, OTHER_ACCOUNT, OTHER_CATEGORY = range(7)

# Токен бота. Фоллбек на явный токен, если переменная окружения не установлена
TOKEN = os.environ.get("TELEGRAM_TOKEN") or "7826192630:AAGyqFR3BlRE_-Wi8lUtC7w8X46dWM07hw0"

# Инициализация
updater = Updater(token=TOKEN, use_context=True)
# Удаляем возможный webhook перед polling
updater.bot.delete_webhook(drop_pending_updates=True)  # сброс всех webhooks и очереди обновлений
dispatcher = updater.dispatcher

# Игнорируем ошибки Conflict, чтобы бот не падал при пересечении getUpdates
import telegram

def error_handler(update, context):
    err = context.error
    if isinstance(err, telegram.error.Conflict):
        logger.warning("Conflict ignored: %s", err)
        return
    logger.error("Unhandled error: %s", err, exc_info=True)

dispatcher.add_error_handler(error_handler)

# Генерация клавиатур
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
        [InlineKeyboardButton("USD", callback_data="USD"), InlineKeyboardButton("руб", callback_data="руб")],
        [InlineKeyboardButton("pounds", callback_data="pounds"), InlineKeyboardButton("tenge", callback_data="tenge")],
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

# Обработчики

def start(update: Update, context: CallbackContext) -> int:
    logger.info("User %s started conversation", update.effective_user.id)
    update.message.reply_text('Привет! Введи название расхода:')
    return NAME

def ask_name(update: Update, context: CallbackContext) -> int:
    context.user_data['name'] = update.message.text
    update.message.reply_text('Введите сумму расхода:')
    return AMOUNT

def ask_amount(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['amount'] = float(update.message.text)
        update.message.reply_text('Выберите счёт:', reply_markup=build_account_keyboard())
        return ACCOUNT
    except ValueError:
        update.message.reply_text('Пожалуйста, введите корректную сумму.')
        return AMOUNT

def ask_account(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    selection = query.data
    if selection == 'other_account':
        query.edit_message_text('Введите другой счёт:')
        return OTHER_ACCOUNT
    context.user_data['account'] = selection
    query.edit_message_text('Выберите валюту расхода:', reply_markup=build_currency_keyboard())
    return CURRENCY

def handle_other_account(update: Update, context: CallbackContext) -> int:
    context.user_data['account'] = update.message.text
    update.message.reply_text('Выберите валюту расхода:', reply_markup=build_currency_keyboard())
    return CURRENCY

def ask_currency(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data['currency'] = query.data
    query.edit_message_text('Выберите категорию:', reply_markup=build_category_keyboard())
    return CATEGORY

def ask_category(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == 'other_category':
        query.edit_message_text('Введите другую категорию:')
        return OTHER_CATEGORY
    context.user_data['category'] = query.data
    return send_data(update, context)

def handle_other_category(update: Update, context: CallbackContext) -> int:
    context.user_data['category'] = update.message.text
    return send_data(update, context)

def send_data(update: Update, context: CallbackContext) -> int:
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
            update.effective_message.reply_text("Данные успешно отправлены!")
        else:
            update.effective_message.reply_text("Ошибка при отправке данных.")
    except Exception as e:
        logger.error("Ошибка при запросе: %s", e)
        update.effective_message.reply_text(f"Ошибка запроса: {e}")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

# Точка входа

def main():
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, ask_name)],
            AMOUNT: [MessageHandler(Filters.text & ~Filters.command, ask_amount)],
            ACCOUNT: [CallbackQueryHandler(ask_account)],
            OTHER_ACCOUNT: [MessageHandler(Filters.text & ~Filters.command, handle_other_account)],
            CURRENCY: [CallbackQueryHandler(ask_currency)],
            CATEGORY: [CallbackQueryHandler(ask_category)],
            OTHER_CATEGORY: [MessageHandler(Filters.text & ~Filters.command, handle_other_category)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(conv)
    updater.start_polling(drop_pending_updates=True)  # отбросить старые апдейты и начать чисто
    updater.idle()

if __name__ == '__main__':
    main()
