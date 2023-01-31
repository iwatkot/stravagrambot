import asyncio
import re

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
from log_handler import Logger, get_log_file

logger = Logger('bot')
TOKEN = config('TOKEN')
BOT_TEMPLATES = get_template('bot_templates')
ADMIN = int(config('ADMIN'))

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot, storage=storage)


class Form(StatesGroup):
    find = State()


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    """Handles the /start command."""
    telegram_id, lang, user_name = unpack_message(message)
    await message.reply(BOT_TEMPLATES[lang][message.text].format(user_name),
                        parse_mode='MarkdownV2')
    await asyncio.sleep(3)
    await bot.send_message(telegram_id, BOT_TEMPLATES[lang]['TOUR'],
                           parse_mode='MarkdownV2')


@dp.message_handler(commands=["auth"])
async def auth_handler(message: types.Message):
    """Handles the /auth command."""
    telegram_id, lang, user_name = unpack_message(message)
    auth_url = BOT_TEMPLATES['oauth_url'].format(telegram_id)
    await message.reply(BOT_TEMPLATES[lang][message.text].format(auth_url),
                        parse_mode='MarkdownV2')


@dp.message_handler(commands=["recent"])
async def recent_handler(message: types.Message):
    """Handles the /recent command."""
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id)
    raw_data = caller.get_activities()
    if raw_data:
        data = formatter.format_activities(raw_data, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(
            telegram_id, BOT_TEMPLATES[lang]['NO_ACTIVITIES'])


@dp.message_handler(commands=["starredsegments"])
async def starred_segments_handler(message: types.Message):
    """Handles the /starredsegments command."""
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id)
    raw_data = caller.raw_data(get_starred_segments=True)
    if raw_data:
        data = formatter.format_starred_segments(raw_data, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(
            telegram_id, BOT_TEMPLATES[lang]['NO_STARRED_SEG'])


@dp.message_handler(commands=["statsall", "statsyear", "weekavg"])
async def stats_handler(message: types.Message):
    """Handles commands for list of activities: /statsall, /statsyear,
    /weekavg."""
    telegram_id, lang, user_name = unpack_message(message)
    stats_command = message.get_command()
    caller = APICaller(telegram_id=telegram_id)
    periods = BOT_TEMPLATES['constants']['periods']
    period = periods.get(stats_command)
    raw_data = caller.get_stats()
    if raw_data:
        data = formatter.format_stats(raw_data, period, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(telegram_id, BOT_TEMPLATES[lang]['NO_STATS'])


@dp.message_handler(regexp_commands=[r'/activity?(?P<value>\w+)'])
async def activity_handler(message: types.Message,
                           regexp_command: re.Match[str]):
    """Handles the /activity<> command to get specified activity."""
    telegram_id, lang, user_name = unpack_message(message)
    value = regexp_command['value']
    caller = APICaller(telegram_id)
    raw_data = caller.raw_data(get_activity=value)
    if raw_data:
        data = formatter.format_activity(raw_data, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(telegram_id, BOT_TEMPLATES[lang]['NO_ACTIVITY'])


@dp.message_handler(regexp_commands=[r'/segment?(?P<value>\w+)'])
async def segment_handler(message: types.Message,
                          regexp_command: re.Match[str]):
    """Handles the /segment<> command to get specified segment."""
    telegram_id, lang, user_name = unpack_message(message)
    value = regexp_command['value']
    caller = APICaller(telegram_id)
    raw_data = caller.raw_data(get_segment=value)
    if raw_data:
        data = formatter.format_segment(raw_data, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(telegram_id, BOT_TEMPLATES[lang]['NO_ACTIVITY'])


@dp.message_handler(regexp_commands=[r'/download?(?P<value>\w+)'])
async def download_handler(message: types.Message,
                           regexp_command: re.Match[str]):
    """Handles the /download<> command to create and send GPX file."""
    telegram_id, lang, user_name = unpack_message(message)
    value = regexp_command['value']
    caller = APICaller(telegram_id)
    filepath = caller.create_gpx(value)
    if filepath:
        file = types.InputFile(filepath)
        await bot.send_document(telegram_id, file)
    else:
        await bot.send_message(
            telegram_id, BOT_TEMPLATES[lang]['BAD_GPX_REQUEST'])


@dp.message_handler(regexp_commands=[r'/gear?(?P<value>\w+)'])
async def gear_handler(message: types.Message,
                       regexp_command: re.Match[str]):
    """Handles the /gear<> command to get specified gear."""
    telegram_id, lang, user_name = unpack_message(message)
    value = regexp_command['value']
    caller = APICaller(telegram_id)
    raw_data = caller.raw_data(get_gear=value)
    if raw_data:
        data = formatter.format_gear(raw_data, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(telegram_id, BOT_TEMPLATES[lang]['NO_GEAR'])


@dp.message_handler(commands=["find"])
async def find_handler(message: types.Message):
    """Handles the /find command. Launches the find state to catch
    message with dates."""
    telegram_id, lang, user_name = unpack_message(message)
    await message.reply(
        BOT_TEMPLATES[lang]['FIND_INIT'], parse_mode='MarkdownV2')
    await Form.find.set()


@dp.message_handler(state='*', commands=['cancel'])
async def cancel_handler(message: types.Message, state: FSMContext):
    """Cancelling current state if it's not None."""
    telegram_id, lang, user_name = unpack_message(message)
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply(BOT_TEMPLATES[lang]['CANCELLED'])


@dp.message_handler(state=Form.find)
async def find_finish(message: types.Message, state: FSMContext):
    """Catches answer for find state and checks if it's correct."""
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
        raw_data = caller.get_activities(before=before, after=after)
        await state.finish()
        if not raw_data:
            await bot.send_message(
                telegram_id, BOT_TEMPLATES[lang]['NO_ACTIVITIES'])
        else:
            data = formatter.format_activities(raw_data, lang)
            await bot.send_message(telegram_id, data,
                                   parse_mode='MarkdownV2')
    else:
        await message.reply(BOT_TEMPLATES[lang]['WRONG_PERIOD'])


# Administration commands.

@dp.message_handler(commands=["users"])
async def users_handler(message: types.Message):
    """Returns formatted list of users with links to the Strava.
    Only available for admin user."""
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
    """Returns txt log file. Only available for admin user."""
    telegram_id, lang, user_name = unpack_message(message)
    if telegram_id == ADMIN:
        log_file = types.InputFile(get_log_file())
        await bot.send_document(telegram_id, log_file)


@dp.message_handler(regexp_commands=[r'/webhook?(?P<action>\w+)'])
async def webhook_handler(message: types.Message,
                          regexp_command: re.Match[str]):
    """Handles operations with Strava webhook subscription (subscribe,
    view and delete). Only available for admin user."""
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


def unpack_message(message: dict) -> tuple:
    """Extracting data from message (telegram_id, lang and user_name."""
    telegram_id = message.from_user.id
    lang = message.from_user.language_code
    lang = lang if lang == 'ru' else 'en'
    user_name = message.from_user.first_name
    logger.debug(BOT_TEMPLATES['log_entry'].format(
        telegram_id, message.text))
    return telegram_id, lang, user_name


if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    executor.start_polling(dp)
