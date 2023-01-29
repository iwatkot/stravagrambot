import os
import json

from re import escape
from datetime import timedelta, datetime
from log_handler import Logger

absolute_path = os.path.dirname(__file__)
logger = Logger(__name__)


def get_template(filename):
    filepath = os.path.join(absolute_path, 'templates/{}.json'.format(
        filename))
    return json.load(open(filepath, encoding='utf-8'))


def get_content(filename, lang):
    filepath = os.path.join(absolute_path, 'content{}_{}.txt'.format(
        filename, lang))
    return open(filepath, encoding='utf-8').readlines()


FORMATTER_URLS = get_template('url_templates')['formatter']
FORMATTER_TEMPLATES = get_template('formatter_templates')
LOG_TEMPLATES = get_template('log_templates')['format_handler']


def format_stats(stats, period, lang):
    logger.debug(LOG_TEMPLATES['stats_init'].format(period, lang))
    useful_data = FORMATTER_TEMPLATES[lang]['stats']['periods'][period]
    divider = None
    if period == 'week':
        divider = datetime.date(datetime.now()).isocalendar().week
    data = []
    for k, v in useful_data.items():
        section = stats.get(k)
        if section.get('count'):
            section['header'] = v
            insert_idle(section)
            if divider:
                divide_stats(section, divider)
            value_formatter(section, modify=True)
            data.append(section)
    message = ''
    for section in data:
        message += use_format_template(section, lang, 'stats')
    return message


def format_activities(activities, lang):
    logger.debug(LOG_TEMPLATES['activities_init'].format(lang))
    for activity in activities:
        locale_type(activity, lang)
        value_formatter(activity, modify=True)
    message = ''
    for activity in activities:
        message += use_format_template(activity, lang, 'activities')
    return message


def format_activity(activity, lang):
    logger.debug(LOG_TEMPLATES['activity_init'].format(lang))
    USEFUL_DATA = FORMATTER_TEMPLATES['useful_data']['activity']
    data = {k: activity.get(k) for k in USEFUL_DATA if activity.get(k)}
    locale_type(data, lang)
    insert_idle(data)
    insert_pace(data)
    data['gear_nickname'] = data.get('gear').get('nickname')
    segment_data = data.get('segment_efforts')
    value_formatter(data, modify=True)
    data['url'] = FORMATTER_URLS['activity_url'] + str(data.get('id'))
    data['download'] = data.get('id')
    message = use_format_template(
        data, lang, 'activity', segment_data=segment_data)
    return message


def format_segment(segment, lang):
    logger.debug(LOG_TEMPLATES['segment_init'].format(lang))
    USEFUL_DATA = FORMATTER_TEMPLATES['useful_data']['segment']
    data = {k: segment.get(k) for k in USEFUL_DATA if segment.get(k)}
    data['type'] = data['activity_type']
    locale_type(data, lang)
    insert_segment_data(data)
    value_formatter(data, modify=True)
    data['url'] = FORMATTER_URLS['segment_url'] + str(data.get('id'))
    message = use_format_template(data, lang, 'segment')
    return message


def value_formatter(data: dict, modify: bool):
    """Modifies the values in the dictonary with specific rules.
    Speed(m/s) to km/h. Time(s) to timedelta. Distance(m) to km.
    Zone aware datetime string to a local datetime string.
    Other values will be filled fith escape symbolds for MD2.
    :param bool modify: Modify the orignal dict or return a new one."""
    if not modify:
        data = data.copy()
    for key, value in data.items():
        if key in FORMATTER_TEMPLATES['convert_keys']['time']:
            data[key] = str(timedelta(seconds=value))
        elif key in FORMATTER_TEMPLATES['convert_keys']['distance']:
            data[key] = escape(str(round(value / 1000, 2)))
        elif key in FORMATTER_TEMPLATES['convert_keys']['speed']:
            data[key] = escape(str(round(value * 3.6, 2)))
        elif key in FORMATTER_TEMPLATES['convert_keys']['date']:
            time = datetime.fromisoformat(value)
            data[key] = escape(datetime.strftime(time, '%Y-%m-%d %H:%M'))
        else:
            data[key] = escape(str(value).strip())
    return data


def insert_idle(data: dict):
    """Iserting idle time and idle percent values into the dict."""
    idle_time = data.get('elapsed_time') - data.get('moving_time')
    idle_percent = round((idle_time / data.get('elapsed_time')) * 100, 2)
    data['idle_time'] = idle_time
    data['idle_percent'] = idle_percent


def pace_formatter(speed):
    pace = datetime.strptime((
        str(timedelta(seconds=(round(1000 / speed))))), '%H:%M:%S')
    return escape(datetime.strftime(pace, '%M:%S'))


def insert_pace(data: dict):
    """Iserting average and maximum pace values into the dict."""
    data['average_pace'] = pace_formatter(data.get('average_speed'))
    data['max_pace'] = pace_formatter(data.get('max_speed'))


def insert_segment_data(data: dict):
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


def locale_type(data: dict, lang: str):
    """Locales the type key in activity dictionary."""
    if lang != 'en':
        localed_activity = FORMATTER_TEMPLATES[lang]['types'].get(
                    data['type'].lower())
        if localed_activity:
            data['type'] = localed_activity


def use_format_template(data: dict, lang: str, type: str, segment_data=None):
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


def divide_stats(data: dict, divider: int):
    """Divides specific stat values with divide value."""
    for k, v in data.items():
        if k in FORMATTER_TEMPLATES['convert_keys']['time']:
            data[k] = round((v) / divider)
        elif k in FORMATTER_TEMPLATES['relative_keys']:
            data[k] = round((v) / divider, 2)


def format_users(users):
    message = '`List of users in the database:`\n\n'
    for user in users:
        id = user[0]
        message += '[{}]({}{}) '.format(
            id, FORMATTER_URLS['user_profile_url'], id)
    return message
