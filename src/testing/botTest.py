import os
import telegram
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("BUYER_TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("BUYER_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
bot.send_message(chat_id=CHAT_ID, text="hi there testtting")
