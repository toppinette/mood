from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
import requests
import os

# Шаги состояния
NAME, AMOUNT, ACCOUNT, CURRENCY, CATEGORY, OTHER_ACCOUNT, OTHER_CATEGORY = range(7)

# Запускаем бота
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Привет! Введи название расхода:')
    return NAME

# Запрос Названия
def ask_name(update: Update, context: CallbackContext) -> int:
    context.user_data['name'] = update.message.text
    update.message.reply_text('Введите сумму расхода:')
    return AMOUNT

# Запрос Суммы
def ask_amount(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['amount'] = float(update.message.text)
        keyboard = [
            [InlineKeyboardButton("Revolut", callback_data='Revolut')],
            [InlineKeyboardButton("BCC", callback_data='BCC')],
            [InlineKeyboardButton("Alta", callback_data='Alta')],
            [InlineKeyboardButton("Другое", callback_data='other_account')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Выберите счёт:', reply_markup=reply_markup)
        return ACCOUNT
    except ValueError:
        update.message.reply_text('Пожалуйста, введите корректную сумму.')
        return AMOUNT

# Обработка выбора счёта
def ask_account(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    account = query.data
    if account == 'other_account':
        context.bot.send_message(chat_id=update.effective_chat.id, text="Введите другой счёт:")
        return OTHER_ACCOUNT
    context.user_data['account'] = account
    return ask_currency_choice(update, context)

# Обработка ввода для "Другое" в счёте
def handle_other_account(update: Update, context: CallbackContext) -> int:
    context.user_data['account'] = update.message.text
    return ask_currency_choice(update, context)

def ask_currency_choice(update, context):
    keyboard = [
        [InlineKeyboardButton("Euro", callback_data='Euro'), InlineKeyboardButton("RSD", callback_data='RSD')],
        [InlineKeyboardButton("USD", callback_data='USD'), InlineKeyboardButton("руб", callback_data='руб')],
        [InlineKeyboardButton("pounds", callback_data='pounds'), InlineKeyboardButton("tenge", callback_data='tenge')]
    ]
    context.bot.send_message(chat_id=update.effective_chat.id, text="Выберите валюту расхода:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CURRENCY

# Обработка выбора валюты
def ask_currency(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data['currency'] = query.data
    keyboard = [
        [InlineKeyboardButton("Рестораны и доставки", callback_data='Рестораны и доставки')],
        [InlineKeyboardButton("Grocery", callback_data='Grocery')],
        [InlineKeyboardButton("Транспорт", callback_data='Транспорт')],
        [InlineKeyboardButton("Путешествия", callback_data='Путешествия')],
        [InlineKeyboardButton("Бытовые", callback_data='Бытовые')],
        [InlineKeyboardButton("Beauty", callback_data='Beauty')],
        [InlineKeyboardButton("Коммуналка", callback_data='Коммуналка')],
        [InlineKeyboardButton("Наличка", callback_data='Наличка')],
        [InlineKeyboardButton("Здоровье", callback_data='Здоровье')],
        [InlineKeyboardButton("Переводы", callback_data='Переводы')],
        [InlineKeyboardButton("Сбережения", callback_data='Сбережения')],
        [InlineKeyboardButton("Другое", callback_data='other_category')]
    ]
    query.edit_message_text(text="Выберите категорию:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CATEGORY

# Обработка выбора категории
def ask_category(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    category = query.data
    if category == 'other_category':
        context.bot.send_message(chat_id=update.effective_chat.id, text="Введите другую категорию:")
        return OTHER_CATEGORY
    context.user_data['category'] = category
    return send_data(update, context)

# Обработка ввода для "Другое" в категории
def handle_other_category(update: Update, context: CallbackContext) -> int:
    context.user_data['category'] = update.message.text
    return send_data(update, context)

# Отправка данных в Google Form
def send_data(update: Update, context: CallbackContext) -> int:
    data = {
        'Название расхода': context.user_data['name'],
        'Сумма расхода': context.user_data['amount'],
        'Счёт': context.user_data['account'],
        'валюта расхода': context.user_data['currency'],
        'Категория': context.user_data['category']
    }
    requests.post('https://script.google.com/macros/s/AKfycbyEMTwPPvCqg4YjhjbikdIvwBo2TmePEBPYeqfBShQ9-XYlaOeuqro1bui2xjB0OfxJSg/exec', data=data)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Данные успешно отправлены!")
    return ConversationHandler.END

# Завершение разговора
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    APP_NAME = "nastyafin"  # Укажите ваше имя приложения на Heroku

    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, ask_name)],
            AMOUNT: [MessageHandler(Filters.text & ~Filters.command, ask_amount)],
            ACCOUNT: [CallbackQueryHandler(ask_account)],
            OTHER_ACCOUNT: [MessageHandler(Filters.text & ~Filters.command, handle_other_account)],
            CURRENCY: [CallbackQueryHandler(ask_currency)],
            CATEGORY: [CallbackQueryHandler(ask_category)],
            OTHER_CATEGORY: [MessageHandler(Filters.text & ~Filters.command, handle_other_category)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(conv_handler)

    # Настройка вебхука
    PORT = int(os.environ.get('PORT', '8443'))
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN
    )
    updater.bot.set_webhook(f"https://{APP_NAME}.herokuapp.com/{TOKEN}")
    updater.idle()

if __name__ == '__main__':
    main()
