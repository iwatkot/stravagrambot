import asyncio
import re
import json
import os

from multiprocessing import Process
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from decouple import config
from datetime import datetime
from pydantic import BaseModel

import format_handler as formatter

from webhook_handler import WebHook
from database_handler import DatabaseSession
from flask_server import run_server
from templates_handler import startup, Constants, Urls
from api_handler import APICaller
from log_handler import Logger, get_log_file, LogTemplates

logger = Logger('bot')
TOKEN = config('TOKEN')
BOT_TEMPLATES = os.path.join(Constants.ABSOLUTE_PATH.value,
                             "templates/bot_templates.json")
BUTTON_TEMPLATES = os.path.join(Constants.ABSOLUTE_PATH.value,
                                "templates/buttons.json")
ADMIN = int(config('ADMIN'))

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot, storage=storage)


class Form(StatesGroup):
    find = State()


class MessageModel(BaseModel):
    START: str
    TOUR: str
    AUTH: str
    NOT_FOUND_IN_DB: str
    ERROR_WHILE_REFRESHING: str
    FIND_INIT: str
    CANCELLED: str
    WRONG_PERIOD: str
    BAD_GPX_REQUEST: str
    NO_ACTIVITIES: str
    NO_STATS: str
    NO_SEGMENT: str
    NO_ACTIVITY: str
    STARRED_SEG: str
    NO_STARRED_SEG: str
    RECENT: str
    GPX: str
    ACTSEG: str
    NO_SEGMENTS: str
    SEGMENTS: str
    WH_SUB_GOOD: str
    WH_SUB_BAD: str
    WH_VIEW_GOOD: str
    WH_VIEW_BAD: str
    WH_DEL_GOOD: str
    WH_DEL_BAD: str


class ButtonModel(BaseModel):
    MAIN_MENU: str
    PROFILE: str
    STATS: str
    ACTIVITIES: str
    AUTH: str
    STARRED_SEGMENTS: str
    STATS_ALL: str
    STATS_YEAR: str
    WEEKAVG: str
    RECENT: str
    LAST: str
    FIND: str
    CANCEL: str

    def main_menu(self):
        return [self.PROFILE, self.STATS, self.ACTIVITIES]

    def profile_menu(self):
        return [self.AUTH, self.STARRED_SEGMENTS, self.MAIN_MENU]

    def stats_menu(self):
        return [self.STATS_ALL, self.STATS_YEAR, self.WEEKAVG, self.MAIN_MENU]

    def activities_menu(self):
        return [self.RECENT, self.LAST, self.FIND, self.MAIN_MENU]


class LocaleMModel(BaseModel):
    ru: MessageModel
    en: MessageModel


class LocaleBModel(BaseModel):
    ru: ButtonModel
    en: ButtonModel


message_data = json.load(open(BOT_TEMPLATES, "r", encoding="utf-8"))
button_data = json.load(open(BUTTON_TEMPLATES, "r", encoding="utf-8"))
message_model = LocaleMModel(ru=MessageModel(**message_data["ru"]),
                             en=MessageModel(**message_data["en"]))
button_model = LocaleBModel(ru=ButtonModel(**button_data["ru"]),
                            en=ButtonModel(**button_data["en"]))
BOT_MESSAGES = message_model.__dict__
BUTTONS = button_model.__dict__


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    """Handles the /start command."""
    telegram_id, lang, user_name = unpack_message(message)
    await message.reply(BOT_MESSAGES[lang].START.format(user_name),
                        parse_mode='MarkdownV2')
    await asyncio.sleep(3)
    await bot.send_message(telegram_id, BOT_MESSAGES[lang].TOUR,
                           parse_mode='MarkdownV2')


@dp.message_handler(commands=["auth"])
async def auth_handler(message: types.Message):
    """Handles the /auth command."""
    telegram_id, lang, user_name = unpack_message(message)

    inline_keyboard = InlineKeyboardMarkup(resize_keyboard=True)
    inline_button = InlineKeyboardButton(
        text='Connect with Strava',
        url=Urls.OAUTH_URL.value.format(telegram_id))
    inline_keyboard.add(inline_button)

    await bot.send_message(telegram_id, BOT_MESSAGES[lang].AUTH,
                           parse_mode='MarkdownV2',
                           reply_markup=inline_keyboard)


@dp.message_handler(commands=["recent"])
async def recent_handler(message: types.Message):
    """Handles the /recent command."""
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id)
    raw_data = caller.get_activities()
    if raw_data:
        data = formatter.format_activities(raw_data, lang)
        await bot.send_message(telegram_id, BOT_MESSAGES[lang].RECENT,
                               reply_markup=generate_inline_keyboard(data),
                               parse_mode='MarkdownV2')
    else:
        await bot.send_message(
            telegram_id, BOT_MESSAGES[lang].NO_ACTIVITIES)


@dp.message_handler(commands=["starredsegments"])
async def starred_segments_handler(message: types.Message):
    """Handles the /starredsegments command."""
    telegram_id, lang, user_name = unpack_message(message)
    caller = APICaller(telegram_id)
    segments = caller.raw_data(get_starred_segments=True)
    if not segments:
        await bot.send_message(
            telegram_id, BOT_MESSAGES[lang].NO_STARRED_SEG)
        return

    inline_buttons = {}
    for segment in segments:
        inline_buttons.update({
            f"segment{segment['id']}":
                f"{segment['name']}"})
    inline_keyboard = generate_inline_keyboard(inline_buttons)
    await bot.send_message(telegram_id, BOT_MESSAGES[lang].STARRED_SEG,
                           reply_markup=inline_keyboard)


@dp.message_handler(commands=["statsall", "statsyear", "weekavg"])
async def stats_handler(message: types.Message):
    """Handles commands for list of activities: /statsall, /statsyear,
    /weekavg."""
    telegram_id, lang, user_name = unpack_message(message)
    stats_command = message.get_command()
    caller = APICaller(telegram_id=telegram_id)
    period = Constants.PERIODS.value.get(stats_command)
    raw_data = caller.get_stats()
    if raw_data:
        data = formatter.format_stats(raw_data, period, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(telegram_id, BOT_MESSAGES[lang].NO_STATS)


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
        await bot.send_message(telegram_id, BOT_MESSAGES[lang].NO_ACTIVITY)


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
        await bot.send_message(telegram_id, BOT_MESSAGES[lang].NO_ACTIVITY)


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
            telegram_id, BOT_MESSAGES[lang].BAD_GPX_REQUEST)


@dp.message_handler(commands=["find"])
async def find_handler(message: types.Message):
    """Handles the /find command. Launches the find state to catch
    message with dates."""
    telegram_id, lang, user_name = unpack_message(message)
    await message.reply(
        BOT_MESSAGES[lang].FIND_INIT, parse_mode='MarkdownV2')
    await Form.find.set()


@dp.message_handler(state='*', commands=['cancel'])
async def cancel_handler(message: types.Message, state: FSMContext):
    """Cancelling current state if it's not None."""
    telegram_id, lang, user_name = unpack_message(message)
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply(BOT_MESSAGES[lang].CANCELLED)


@dp.message_handler(state=Form.find)
async def find_finish(message: types.Message, state: FSMContext):
    """Catches answer for find state and checks if it's correct."""
    telegram_id, lang, user_name = unpack_message(message)
    try:
        dates = message.text.split()
        after, before = tuple(map(
            lambda x: datetime.strptime(x, "%Y-%m-%d").timestamp(), dates))
    except Exception:
        await message.reply(BOT_MESSAGES[lang].WRONG_PERIOD)
        return
    if 0 < before - after < (120 * 24 * 60 * 60):
        caller = APICaller(telegram_id=telegram_id)
        raw_data = caller.get_activities(before=before, after=after)
        await state.finish()
        if not raw_data:
            await bot.send_message(
                telegram_id, BOT_MESSAGES[lang].NO_ACTIVITIES)
        else:
            data = formatter.format_activities(raw_data, lang)
            await bot.send_message(telegram_id, BOT_MESSAGES[lang].RECENT,
                                   reply_markup=generate_inline_keyboard(data),
                                   parse_mode='MarkdownV2')
    else:
        await message.reply(BOT_MESSAGES[lang].WRONG_PERIOD)


# Keyboard generators.

def generate_inline_keyboard(inline_buttons: dict):
    inline_keyboard = InlineKeyboardMarkup(resize_keyboard=True)
    for key, value in inline_buttons.items():
        inline_button = InlineKeyboardButton(text=value, callback_data=key)
        inline_keyboard.add(inline_button)
    return inline_keyboard


# Callback handlers.

@dp.callback_query_handler(text_contains='activity')
async def activity_callback(callback_query: types.CallbackQuery):
    telegram_id, lang, user_name = unpack_message(callback_query)
    activity_id = callback_query.data.split('activity')[1]

    inline_buttons = {
        f"gpx{activity_id}": BOT_MESSAGES[lang].GPX,
        f"actseg{activity_id}": BOT_MESSAGES[lang].ACTSEG}
    inline_keyboard = generate_inline_keyboard(inline_buttons)

    caller = APICaller(telegram_id)
    raw_data = caller.raw_data(get_activity=activity_id)
    if raw_data:
        data = formatter.format_activity(raw_data, lang)
        await bot.send_message(telegram_id, data,
                               reply_markup=inline_keyboard,
                               parse_mode='MarkdownV2')
    else:
        await bot.send_message(telegram_id, BOT_MESSAGES[lang].NO_ACTIVITY)


@dp.callback_query_handler(text_contains='gpx')
async def gpx_callback(callback_query: types.CallbackQuery):
    telegram_id, lang, user_name = unpack_message(callback_query)
    activity_id = callback_query.data.split('gpx')[1]

    caller = APICaller(telegram_id)
    filepath = caller.create_gpx(activity_id)

    if filepath:
        file = types.InputFile(filepath)
        await bot.send_document(telegram_id, file)
    else:
        await bot.send_message(
            telegram_id, BOT_MESSAGES[lang].BAD_GPX_REQUEST)


@dp.callback_query_handler(text_contains='actseg')
async def actseg_callback(callback_query: types.CallbackQuery):
    telegram_id, lang, user_name = unpack_message(callback_query)
    activity_id = callback_query.data.split('actseg')[1]

    caller = APICaller(telegram_id)
    raw_data = caller.raw_data(get_activity=activity_id)

    segments = raw_data['segment_efforts']
    if not segments:
        await bot.send_message(telegram_id, BOT_MESSAGES[lang].NO_SEGMENTS)
        return
    inline_buttons = {}
    for segment in segments:
        inline_buttons.update({
            f"segment{segment['segment']['id']}":
                f"{segment['segment']['name']}"})
    inline_keyboard = generate_inline_keyboard(inline_buttons)
    await bot.send_message(telegram_id, BOT_MESSAGES[lang].SEGMENTS,
                           reply_markup=inline_keyboard)


@dp.callback_query_handler(text_contains='segment')
async def segment_callback(callback_query: types.CallbackQuery):
    telegram_id, lang, user_name = unpack_message(callback_query)
    segment_id = callback_query.data.split('segment')[1]

    caller = APICaller(telegram_id)
    raw_data = caller.raw_data(get_segment=segment_id)

    if raw_data:
        data = formatter.format_segment(raw_data, lang)
        await bot.send_message(telegram_id, data, parse_mode='MarkdownV2')
    else:
        await bot.send_message(telegram_id, BOT_MESSAGES[lang].NO_ACTIVITY)


# Administration commands.

@dp.message_handler(commands=["users"])
async def users_handler(message: types.Message):
    """Returns formatted list of users with links to the Strava.
    Only available for admin user."""
    telegram_id, lang, user_name = unpack_message(message)
    if telegram_id == ADMIN:
        users_session = DatabaseSession(telegram_id)
        users = users_session.get_users()
        users_session.disconnect()
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
                    telegram_id, BOT_MESSAGES[lang].WH_SUB_GOOD.format(
                        result))
            else:
                await bot.send_message(
                    telegram_id, BOT_MESSAGES[lang].WH_SUB_BAD)
        elif action == 'view':
            result = webhook.view()
            if result:
                await bot.send_message(
                    telegram_id, BOT_MESSAGES[lang].WH_VIEW_GOOD.format(
                        result))
            else:
                await bot.send_message(
                    telegram_id, BOT_MESSAGES[lang].WH_VIEW_BAD)
        elif action == 'delete':
            webhook.view()
            result = webhook.delete()
            if result:
                await bot.send_message(
                    telegram_id, BOT_MESSAGES[lang].WH_DEL_GOOD)
            else:
                await bot.send_message(
                    telegram_id, BOT_MESSAGES[lang].WH_DEL_BAD)


# Message and callbacks unpackers.


def unpack_message(message: dict) -> tuple:
    """Extracting data from message (telegram_id, lang and user_name."""
    telegram_id = message.from_user.id
    lang = message.from_user.language_code
    lang = lang if lang == 'ru' else 'en'
    user_name = message.from_user.first_name
    try:
        logger.debug(LogTemplates['bot'].LOG_MESSAGE.format(
            telegram_id, message.text))
    except AttributeError:
        logger.debug(LogTemplates['bot'].LOG_CALLBACK.format(
            telegram_id, message.data))
    return telegram_id, lang, user_name


if __name__ == "__main__":
    startup()
    server_process = Process(target=run_server)
    server_process.start()
    executor.start_polling(dp)
