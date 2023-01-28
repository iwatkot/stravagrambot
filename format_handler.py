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
    filepath = os.path.join(absolute_path, 'content/{}_{}.txt'.format(
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
                for k, v in section.items():
                    if k in FORMATTER_TEMPLATES['convert_keys']['time']:
                        section[k] = round((v) / divider)
                    elif k in FORMATTER_TEMPLATES['relative_keys']:
                        section[k] = round((v) / divider, 2)
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


def segment(segment, lang='en'):        # REFACTOR
    if segment:
        logger.debug(LOG_TEMPLATES['segment_init'].format(lang))
        useful_data = ['id', 'name', 'activity_type', 'distance',
                       'average_grade', 'maximum_grade',
                       'total_elevation_gain', 'climg_category',
                       'effort_count', 'athlete_count',
                       'athlete_segment_stats', 'xoms', 'local_legend']
        segment_data = {k: segment.get(k) for k in useful_data}
        segment_id = segment_data.get('id')
        segment_name = segment_data.get('name')
        activity_type = segment_data.get('activity_type').lower()
        if lang != 'en':
            localed_activity = FORMATTER_TEMPLATES[lang]['types'].get(
                activity_type)
            if localed_activity:
                activity_type = localed_activity
        distance = segment_data.get('distance')
        average_grade = segment_data.get('average_grade')
        maximum_grade = segment_data.get('maximum_grade')
        elevation = segment_data.get('total_elevation_gain')
        climb_category = segment_data.get('climb_category')
        total_efforts = segment_data.get('effort_count')
        total_athletes = segment_data.get('athlete_count')
        athlete_stats = segment_data.get('athlete_segment_stats')
        if athlete_stats:
            pr_time = athlete_stats.get('pr_elapsed_time')
            pr_time = timedelta(seconds=pr_time)
            pr_date = athlete_stats.get('pr_date')
            pr_id = athlete_stats.get('pr_activity_id')
            efforts = athlete_stats.get('effort_count')
        xoms = segment_data.get('xoms')
        if xoms:
            kom = xoms.get('kom')
            qom = xoms.get('qom')
        local_legend = segment_data.get('local_legend')
        if local_legend:
            ll_name = local_legend.get('title')
            ll_efforts = local_legend.get('effort_count')
        message = ''
        message += FORMATTER_TEMPLATES[lang]['seg']['name_type'].format(
            segment_name, activity_type)
        if climb_category:
            message += FORMATTER_TEMPLATES[lang]['seg']['cat'].format(
                climb_category)
        message += FORMATTER_TEMPLATES[lang]['seg']['dst_elev'].format(
            distance, elevation)
        message += FORMATTER_TEMPLATES[lang]['seg']['grade'].format(
            average_grade, maximum_grade)
        message += FORMATTER_TEMPLATES[lang]['seg']['segment_info'].format(
            total_efforts, total_athletes)
        message += FORMATTER_TEMPLATES[lang]['seg']['xoms'].format(
            kom, qom)
        message += FORMATTER_TEMPLATES[lang]['seg']['your_stats'].format(
            pr_time, efforts, pr_date, pr_id)
        message += FORMATTER_TEMPLATES[lang]['seg']['local_legend'].format(
            ll_name, ll_efforts)
        message += FORMATTER_TEMPLATES[lang]['seg']['strava_url'].format(
            FORMATTER_URLS['segment_url'], segment_id)
        return message


def timez_formatter(timestr):
    unpacked_time = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%SZ')
    return escape(datetime.strftime(unpacked_time, '%Y-%m-%d %H:%m'))


def speed_formatter(speed):
    return escape(str(round(speed * 3.6, 2)))


def distance_formatter(distance):
    return escape(str(round(distance / 1000, 2)))


def pace_formatter(speed):
    pace = datetime.strptime((
        str(timedelta(seconds=(round(1000 / speed))))), '%H:%M:%S')
    return escape(datetime.strftime(pace, '%M:%S'))


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
            data[key] = distance_formatter(value)
        elif key in FORMATTER_TEMPLATES['convert_keys']['speed']:
            data[key] = speed_formatter(value)
        elif key in FORMATTER_TEMPLATES['convert_keys']['date']:
            data[key] = timez_formatter(value)
        else:
            data[key] = escape(str(value).strip())
    return data


def insert_idle(data: dict):
    """Iserting idle time and idle percent values into the dict."""
    idle_time = data.get('elapsed_time') - data.get('moving_time')
    idle_percent = round((idle_time / data.get('elapsed_time')) * 100, 2)
    data['idle_time'] = idle_time
    data['idle_percent'] = idle_percent


def insert_pace(data: dict):
    """Iserting average and maximum pace values into the dict."""
    data['average_pace'] = pace_formatter(data.get('average_speed'))
    data['max_pace'] = pace_formatter(data.get('max_speed'))


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


def format_users(users):
    message = '`List of users in the database:`\n\n'
    for user in users:
        id = user[0]
        message += '[{}]({}{}) '.format(
            id, FORMATTER_URLS['user_profile_url'], id)
    return message
