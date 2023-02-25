import os
import json
from inspect import stack
from enum import Enum

from re import escape
from datetime import timedelta, datetime
from log_handler import Logger, LogTemplates

absolute_path = os.path.dirname(__file__)
logger = Logger(__name__)


class Urls(Enum):
    ACTIVITY = "https://www\\.strava\\.com/activities/{}"
    PROFILE = "https://www.strava.com/athletes/"
    SEGMENT = "https://www\\.strava\\.com/segments/{}"
    STRAVA_API = "https://www.strava.com/api/v3/oauth/token"

    def __str__(self):
        return f"{self.value}"


def get_template(filename: str) -> dict:
    """Returns data from the specified JSON file."""
    filepath = os.path.join(absolute_path, 'templates/{}.json'.format(
        filename))
    return json.load(open(filepath, encoding='utf-8'))


def get_content(filename: str, lang: str) -> list:
    """Returns data from the specified TXT file with chosen language."""
    filepath = os.path.join(absolute_path, 'content{}_{}.txt'.format(
        filename, lang))
    return open(filepath, encoding='utf-8').readlines()


FORMATTER_TEMPLATES = get_template('formatter_templates')


def format_stats(raw_data: dict, period: str, lang: str) -> str:
    """Formats stats raw data with specific template
    and returns escaped message, ready for MD2 markup."""
    logger.debug(LogTemplates[__name__].FUNCTION_INIT.format(
        stack()[0][3], lang))

    header_templates = FORMATTER_TEMPLATES[lang]['stats']['periods'][period]
    divider = None
    if period == 'week':
        # Finding number of the current week.
        divider = datetime.date(datetime.now()).isocalendar().week

    data = []
    for k, v in header_templates.items():
        raw_section = raw_data.get(k)
        if raw_section.get('count'):
            # Preparing dict for formatting with template.
            raw_section['header'] = v
            raw_section['average_speed'] = round(raw_section.get(
                'distance') / raw_section.get('moving_time'), 2)
            raw_section['average_pace'] = pace_formatter(
                raw_section.get('average_speed'))
            insert_idle(raw_section)
            if divider:
                divide_stats(raw_section, divider)
            # Converting values in the dict.
            value_formatter(raw_section)
            data.append(raw_section)
    # Generating result message with template.
    message = ''
    for section in data:
        message += use_format_template(section, lang, 'stats')
    return message


def format_activities(data: list, lang: str) -> str:
    """Formats list of activities raw data with specific template
    and returns escaped message, ready for MD2 markup."""
    logger.debug(LogTemplates[__name__].FUNCTION_INIT.format(
        stack()[0][3], lang))
    # Formatting each dict in the list.
    for section in data:
        locale_type(section, lang)
        value_formatter(section)
    # Generating result message with template.
    message = ''
    for section in data:
        message += use_format_template(section, lang, 'activities')
    return message


def format_activity(data: dict, lang: str) -> str:
    """Formats activity raw data with specific template
    and returns escaped message, ready for MD2 markup."""
    logger.debug(LogTemplates[__name__].FUNCTION_INIT.format(
        stack()[0][3], lang))
    locale_type(data, lang)
    insert_idle(data)
    insert_pace(data)
    # Preparing dict for formatting with template.
    data['gear_nickname'] = data.get('gear').get('nickname')
    data['gear_id'] = data.get('gear').get('id')
    segment_data = data.get('segment_efforts')
    # Formatting values in the data dict.
    value_formatter(data)
    # Adding keys with new data.
    data['url'] = Urls.ACTIVITY.value.format(data.get('id'))
    data['download'] = data.get('id')
    # Generating result message with template.
    message = use_format_template(
        data, lang, 'activity', segment_data=segment_data)
    return message


def format_segment(data: dict, lang: str) -> str:
    """Formats segment raw data with specific template
    and returns escaped message, ready for MD2 markup."""
    logger.debug(LogTemplates[__name__].FUNCTION_INIT.format(
        stack()[0][3], lang))
    # Preparing dict for formatting with template.
    data['type'] = data['activity_type']
    locale_type(data, lang)
    insert_segment_data(data)
    # Formatting values in the data dict.
    value_formatter(data)
    data['url'] = Urls.SEGMENT.value.format(data.get('id'))
    # Generating result message with template.
    message = use_format_template(data, lang, 'segment')
    return message


def format_starred_segments(data: list, lang: str) -> str:
    """Formats starred segments raw data with specific template
    and returns escaped message, ready for MD2 markup."""
    logger.debug(LogTemplates[__name__].FUNCTION_INIT.format(
        stack()[0][3], lang))
    # Formatting each dict in the list.
    for section in data:
        # Preparing data dict for formatting.
        section['type'] = section['activity_type']
        locale_type(section, lang)
        # Formatting values in the data dict.
        value_formatter(section)
    # Generating result message with template.
    message = ''
    for section in data:
        message += use_format_template(section, lang, 'starred_segments')
    return message


def format_gear(raw_data: dict, lang: str) -> str:
    """Formats gear raw data with specific template
    and returns escaped message, ready for MD2 markup."""
    value_formatter(raw_data)
    message = use_format_template(raw_data, lang, 'gear')
    return message


def timez_formatter(timestr):
    unpacked_time = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%SZ')
    return escape(datetime.strftime(unpacked_time, '%Y-%m-%d %H:%m'))


def value_formatter(data: dict) -> None:
    """Modifies the values in the dictonary with specific rules.
    Speed(m/s) to km/h. Time(s) to timedelta. Distance(m) to km.
    Zone aware datetime string to a local datetime string.
    Other values will be filled fith escape symbolds for MD2."""
    for key, value in data.items():
        if key in FORMATTER_TEMPLATES['convert_keys']['time']:
            data[key] = str(timedelta(seconds=value))
        elif key in FORMATTER_TEMPLATES['convert_keys']['distance']:
            data[key] = escape(str(round(value / 1000, 2)))
        elif key in FORMATTER_TEMPLATES['convert_keys']['speed']:
            data[key] = escape(str(round(value * 3.6, 2)))
        elif key in FORMATTER_TEMPLATES['convert_keys']['date']:
            data[key] = timez_formatter(value)
        else:
            data[key] = escape(str(value).strip())


def insert_idle(data: dict) -> None:
    """Iserting idle time and idle percent values into the dict."""
    idle_time = data.get('elapsed_time') - data.get('moving_time')
    idle_percent = round((idle_time / data.get('elapsed_time')) * 100, 2)
    data['idle_time'] = idle_time
    data['idle_percent'] = idle_percent


def pace_formatter(speed: int) -> str:
    """Converts speed in m/s to pace format (time for 1 km)."""
    pace = datetime.strptime((
        str(timedelta(seconds=(round(1000 / speed))))), '%H:%M:%S')
    return escape(datetime.strftime(pace, '%M:%S'))


def insert_pace(data: dict) -> None:
    """Inserting average and maximum pace values into the dict."""
    data['average_pace'] = pace_formatter(data.get('average_speed'))
    data['max_pace'] = pace_formatter(data.get('max_speed'))


def insert_segment_data(data: dict) -> None:
    """Inserting segment data into the dict."""
    xom_data = data.get('xoms')
    athlete_data = data.get('athlete_segment_stats')
    local_legend = data.get('local_legend')
    if xom_data:
        data['kom'] = xom_data.get('kom')
        data['qom'] = xom_data.get('qom')
    if athlete_data:
        data['pr_elapsed_time'] = athlete_data.get('pr_elapsed_time')
        data['athlete_effort_count'] = athlete_data.get('effort_count')
        data['pr_date'] = athlete_data.get('pr_date')
        data['pr_activity_id'] = athlete_data.get('pr_activity_id')
    if local_legend:
        data['ll_title'] = local_legend.get('title')
        data['ll_efforts'] = local_legend.get('effort_count')


def locale_type(data: dict, lang: str) -> None:
    """Locales the type key in activity dictionary."""
    if lang != 'en':
        localed_activity = FORMATTER_TEMPLATES[lang]['types'].get(
                    data['type'].lower())
        if localed_activity:
            data['type'] = localed_activity


def use_format_template(data: dict, lang: str,
                        type: str, segment_data: dict = None) -> str:
    """Formats data dictionary with specified template."""
    format_template = FORMATTER_TEMPLATES[lang][type]
    message = ''
    for key in format_template:
        if data.get(key):
            message += format_template[key].format(data[key])
    if segment_data:
        message += format_template['segment_data']['segment_list']
        for segment in segment_data:
            segment_name = segment['segment'].get('name')
            segment_id = segment['segment'].get('id')
            message += format_template['segment_data']['segment'].format(
                segment_name, segment_id)
    return message


def divide_stats(data: dict, divider: int) -> None:
    """Divides specific stat values with divide value."""
    for k, v in data.items():
        if k in FORMATTER_TEMPLATES['convert_keys']['time']:
            data[k] = round((v) / divider)
        elif k in FORMATTER_TEMPLATES['relative_keys']:
            data[k] = round((v) / divider, 2)


def format_users(users: list) -> str:
    """Formatting list of strava ids from the database to MD2 with links."""
    message = FORMATTER_TEMPLATES['users_template'].format(len(users))
    for user in users:
        message += '[{}]({}{}) '.format(user, Urls.PROFILE.value, user)
    return message
