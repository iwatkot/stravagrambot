import asyncio
import re
import os

from multiprocessing import Process
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from decouple import config
from datetime import datetime

import format_handler as formatter

from webhook_handler import WebHook
from database_handler import DataBase
from flask_server import run_server
from format_handler import get_template
from api import APICaller
from log_handler import Logger

logger = Logger('bot')
TOKEN = config('TOKEN')
BOT_TEMPLATES = get_template('bot_templates')
URL_TEMPLATES = get_template('url_templates')
LOG_TEMPLATES = get_template('log_templates')['main']
LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs/main_log.txt')
ADMIN = int(config('ADMIN'))

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot, storage=storage)


class Form(StatesGroup):
    find = State()


class Replyer:
    def __init__(self, message):
        self.message = message
        self.telegram_id = message.from_user.id
        lang = self.message.from_user.language_code
        self.lang = lang if lang == 'ru' else 'en'
        self.first_name = message.from_user.first_name

    async def basic_commands(self):
        basic_command = self.message.get_command()
        if basic_command == '/start':
            await self.message.reply(
                BOT_TEMPLATES[self.lang][self.message.text].format(
                    self.first_name), parse_mode='MarkdownV2')
            await asyncio.sleep(3)
            await bot.send_message(
                self.telegram_id, BOT_TEMPLATES[self.lang]['TOUR'],
                parse_mode='MarkdownV2')
        elif basic_command == '/auth':
            auth_url = URL_TEMPLATES['oauth']['access_request'].format(
                self.telegram_id)
            await self.message.reply(
                BOT_TEMPLATES[self.lang][self.message.text].format(auth_url),
                parse_mode='MarkdownV2')
        elif basic_command == '/recent':
            caller = APICaller(telegram_id=self.telegram_id)
            activities = caller.activities()
            if activities:
                formatted_activities = formatter.format_activities(
                    activities=activities, lang=self.lang)
                await bot.send_message(self.telegram_id, formatted_activities,
                                       parse_mode='MarkdownV2')
            else:
                await bot.send_message(
                    self.telegram_id,
                    BOT_TEMPLATES[self.lang]['NO_ACTIVITIES'])

    async def stats_commands(self):
        stats_command = self.message.get_command()
        caller = APICaller(telegram_id=self.telegram_id)
        periods = BOT_TEMPLATES['constants']['periods']
        period = periods.get(stats_command)
        stats = caller.get_stats()
        if stats:
            formatted_stats = formatter.format_stats(stats, period, self.lang)
            await bot.send_message(
                self.telegram_id, formatted_stats, parse_mode='MarkdownV2')
        else:
            await bot.send_message(
                self.telegram_id, BOT_TEMPLATES[self.lang]['NO_STATS'])


@dp.message_handler(commands=["start", "auth", "recent"])
async def basic_commands(message: types.Message):
    r = Replyer(message)
    await r.basic_commands()


@dp.message_handler(commands=["statsall", "statsyear", "weekavg"])
async def stats_handler(message: types.Message):
    r = Replyer(message)
    await r.stats_commands()


@dp.message_handler(regexp_commands=[r'/activity?(?P<activity_id>\w+)'])
async def activity_handler(message: types.Message,
                           regexp_command: re.Match[str]):
    # Handles the '/activity' command.
    activity_id = regexp_command['activity_id']
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id=telegram_id)
    activity = caller.activity(activity_id)
    formatted_activity = formatter.format_activity(activity, lang)
    await bot.send_message(telegram_id, formatted_activity,
                           parse_mode='MarkdownV2')


@dp.message_handler(regexp_commands=[r'/segment?(?P<segment_id>\w+)'])
async def segment_handler(message: types.Message,
                          regexp_command: re.Match[str]):
    # Handles the '/segment' command.
    segment_id = regexp_command['segment_id']
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id=telegram_id)
    segment = caller.segment(segment_id)
    if segment:
        formatted_segment = formatter.format_segment(
            segment=segment, lang=lang)
        await bot.send_message(telegram_id, formatted_segment,
                               parse_mode='MarkdownV2')
    else:
        await bot.send_message(
            telegram_id, BOT_TEMPLATES[lang]['NO_SEGMENT'])


@dp.message_handler(regexp_commands=[r'/download?(?P<activity_id>\w+)'])
async def gpx_handler(message: types.Message,
                      regexp_command: re.Match[str]):
    activity_id = regexp_command['activity_id']
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id=telegram_id)
    caller.activity(activity_id)
    filepath = caller.create_gpx()
    if filepath:
        file = types.InputFile(filepath)
        await bot.send_document(telegram_id, file)
    else:
        await message.reply(BOT_TEMPLATES[lang]['BAD_GPX_REQUEST'])


@dp.message_handler(commands=["find"])
async def find_handler(message: types.Message):
    # Handles the '/find' command.
    telegram_id, lang, user_name = unpack_message(message)
    await message.reply(
        BOT_TEMPLATES[lang]['FIND_INIT'], parse_mode='MarkdownV2')
    await Form.find.set()


@dp.message_handler(state='*', commands=['cancel'])
async def cancel_handler(message: types.Message, state: FSMContext):
    # Handles the '/cancel' command.
    telegram_id, lang, user_name = unpack_message(message)
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply(BOT_TEMPLATES[lang]['CANCELLED'])


@dp.message_handler(state=Form.find)
async def find_finish(message: types.Message, state: FSMContext):
    # Catching the answer for the /find command.
    telegram_id, lang, user_name = unpack_message(message)
    try:
        dates = message.text.split()
        after, before = tuple(map(
            lambda x: datetime.strptime(x, "%Y-%m-%d").timestamp(), dates))
    except Exception:
        await message.reply(BOT_TEMPLATES[lang]['WRONG_PERIOD'])
        return
    if 0 < before - after < (120 * 24 * 60 * 60):
        caller = APICaller(telegram_id=telegram_id)
        activities = caller.activities(before=before, after=after)
        await state.finish()
        if not activities:
            await bot.send_message(
                telegram_id, BOT_TEMPLATES[lang]['NO_ACTIVITIES'])
        else:
            formatted_activities = formatter.activities(activities=activities)
            await bot.send_message(telegram_id, formatted_activities,
                                   parse_mode='MarkdownV2')
    else:
        await message.reply(BOT_TEMPLATES[lang]['WRONG_PERIOD'])


# Administration commands.
@dp.message_handler(commands=["users"])
async def users_handler(message: types.Message):
    # Handles the '/users' command.
    telegram_id, lang, user_name = unpack_message(message)
    if telegram_id == ADMIN:
        users_session = DataBase(telegram_id=telegram_id)
        users = users_session.get_users()
        formatted_message = formatter.format_users(users)
        await bot.send_message(telegram_id, formatted_message,
                               disable_web_page_preview=True,
                               parse_mode='MarkdownV2')


@dp.message_handler(commands=["logs"])
async def logs_handler(message: types.Message):
    # Handles the '/users' command.
    telegram_id, lang, user_name = unpack_message(message)
    if telegram_id == ADMIN:
        file = types.InputFile(LOG_FILE)
        await bot.send_document(telegram_id, file)


@dp.message_handler(regexp_commands=[r'/webhook?(?P<action>\w+)'])
async def webhook_handler(message: types.Message,
                          regexp_command: re.Match[str]):
    action = regexp_command['action']
    telegram_id, lang, user_name = unpack_message(message)
    if telegram_id == ADMIN:
        webhook = WebHook()
        if action == 'subscribe':
            result = webhook.subscribe()
            if result:
                await bot.send_message(
                    telegram_id, BOT_TEMPLATES['admin']['WH_SUB_GOOD'].format(
                        result))
            else:
                await bot.send_message(
                    telegram_id, BOT_TEMPLATES['admin']['WH_SUB_BAD'])
        elif action == 'view':
            result = webhook.view()
            if result:
                await bot.send_message(
                    telegram_id, BOT_TEMPLATES['admin']['WH_VIEW_GOOD'].format(
                        result))
            else:
                await bot.send_message(
                    telegram_id, BOT_TEMPLATES['admin']['WH_VIEW_BAD'])
        elif action == 'delete':
            webhook.view()
            result = webhook.delete()
            if result:
                await bot.send_message(
                    telegram_id, BOT_TEMPLATES['admin']['WH_DEL_GOOD'])
            else:
                await bot.send_message(
                    telegram_id, BOT_TEMPLATES['admin']['WH_DEL_BAD'])


def unpack_message(message):
    # Extractng data from message.
    telegram_id = message.from_user.id
    lang = message.from_user.language_code
    lang = lang if lang == 'ru' else 'en'
    user_name = message.from_user.first_name
    logger.debug(LOG_TEMPLATES['MESSAGE_FROM_USER'].format(
        telegram_id, message.text))
    return telegram_id, lang, user_name


if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    executor.start_polling(dp)
