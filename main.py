# import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from decouple import config

from templates_handler import get_template
from database_handler import get_access_token
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
    telegram_id, lang, user_name = unpack_message(message, no_token=True)
    await message.reply(BOT_TEMPLATES[lang][message.text].format(user_name),
                        parse_mode='MarkdownV2')


@dp.message_handler(commands=["auth"])
async def auth_handler(message: types.Message):
    # Handles the '/auth' command.
    telegram_id, lang, user_name = unpack_message(message, no_token=True)
    auth_url = URL_TEMPLATES['oauth']['access_request'].format(telegram_id)
    await message.reply(BOT_TEMPLATES[lang][message.text].format(auth_url),
                        parse_mode='MarkdownV2')


@dp.message_handler(commands=["check"])
async def check_handler(message: types.Message):
    # Handles the '/check' command.
    access_token, telegram_id, lang, user_name = unpack_message(message)
    if access_token:
        await bot.send_message(telegram_id, access_token)
    elif access_token is None:
        await bot.send_message(
            telegram_id, BOT_TEMPLATES[lang]['ERROR_WHILE_REFRESHING'])
    else:
        await bot.send_message(
            telegram_id, BOT_TEMPLATES[lang]['NOT_FOUND_IN_DB'])


def unpack_message(message, no_token=False):
    # Extractng data from message.
    telegram_id = message.from_user.id
    lang = message.from_user.language_code
    lang = lang if lang == 'ru' else 'en'
    user_name = message.from_user.first_name
    if no_token:
        return telegram_id, lang, user_name
    else:
        return get_access_token(telegram_id), telegram_id, lang, user_name

if __name__ == "__main__":
    executor.start_polling(dp)
