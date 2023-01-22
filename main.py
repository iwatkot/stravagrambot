# import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from decouple import config

from templates_handler import get_template
from api import APICaller
# from log_handler import Logger

# logger = Logger('main')
TOKEN = config('TOKEN')
BOT_TEMPLATES = get_template('bot_templates')
URL_TEMPLATES = get_template('url_templates')

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot, storage=storage)


class Form(StatesGroup):
    bugreport = State()


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    # Handles the '/start' command.
    telegram_id, lang, user_name = unpack_message(message)
    await message.reply(BOT_TEMPLATES[lang][message.text].format(user_name),
                        parse_mode='MarkdownV2')


@dp.message_handler(commands=["auth"])
async def auth_handler(message: types.Message):
    # Handles the '/auth' command.
    telegram_id, lang, user_name = unpack_message(message)
    auth_url = URL_TEMPLATES['oauth']['access_request'].format(telegram_id)
    await message.reply(BOT_TEMPLATES[lang][message.text].format(auth_url),
                        parse_mode='MarkdownV2')


@dp.message_handler(commands=["getstats"])
async def check_handler(message: types.Message):
    # Handles the '/getstats' command.
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id=telegram_id)
    stats = caller.get_stats()
    await bot.send_message(telegram_id, BOT_TEMPLATES[lang]['STATS'].format(stats))


def unpack_message(message):
    # Extractng data from message.
    telegram_id = message.from_user.id
    # lang = message.from_user.language_code
    # lang = lang if lang == 'ru' else 'en'
    lang = 'en'  # temporary while no locale
    user_name = message.from_user.first_name
    return telegram_id, lang, user_name


if __name__ == "__main__":
    executor.start_polling(dp)
