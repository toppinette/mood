import os, json, logging
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Config via ENV ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
SHEET_ID = os.environ.get("SHEET_ID", "1AyqXSE39goUnW2os1lnmUdMKscYdio-_lkpCWSpvJ7k")
SHEET_NAME = os.environ.get("SHEET_NAME", "Sheet1")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "hook")
PUBLIC_URL = os.environ["PUBLIC_URL"]          # e.g. https://your-service.onrender.com
PORT = int(os.environ.get("PORT", "10000"))
SA_DICT = json.loads(os.environ["GOOGLE_SA_JSON"])

# --- Google Sheets client ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(SA_DICT, scopes=SCOPES)
gc = gspread.authorize(creds)
ws = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬇️ worse than yesterday", callback_data="-1"),
        InlineKeyboardButton("🟰 same as yesterday", callback_data="0"),
        InlineKeyboardButton("⬆️ better than yesterday", callback_data="1"),
    ]])
    await update.message.reply_text("how are you today?", reply_markup=kb)

async def on_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    value = int(q.data)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # append: col A timestamp, col B value
    ws.append_row([ts, value])
    await q.edit_message_text("thank you for sharing! See you tomorrow 💜")

async def on_startup(app: Application):
    # set webhook to Render public URL + secret path
    url = f"{PUBLIC_URL}/{WEBHOOK_SECRET}"
    await app.bot.set_webhook(url=url, secret_token=WEBHOOK_SECRET)
    logger.info("Webhook set to %s", url)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(on_choice))
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_SECRET,
        secret_token=WEBHOOK_SECRET,
        webhook_url=f"{PUBLIC_URL}/{WEBHOOK_SECRET}",
        start_webhook=True,
        stop_signals=None,
        drop_pending_updates=True,
        post_init=on_startup,
    )

if __name__ == "__main__":
    main()
