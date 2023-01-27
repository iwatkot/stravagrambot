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


def stats(stats, period, lang='en'):
    logger.debug(LOG_TEMPLATES['stats_init'].format(period, lang))
    if period == 'week':
        data_dict = FORMATTER_TEMPLATES[lang]['weekavg'].copy()
        today = datetime.date(datetime.now())
        divider = today.isocalendar().week
    else:
        data_dict = FORMATTER_TEMPLATES[lang]['stats'].copy()
        if period == 'year':
            del data_dict['all_ride_totals']
            del data_dict['all_run_totals']
        divider = 1
    message = ''
    for k, v in data_dict.items():
        stat_dict = stats.get(k)
        count = stat_dict.get('count')
        if count:
            message += '`{}`\n'.format(v)
            for k, v in stat_dict.items():
                message += "*{}*: ".format(
                    FORMATTER_TEMPLATES[lang]['stats_for_humans'][k])
                if 'distance' in k:
                    v = v / divider
                    message += "`{} km`\n".format(distance_formatter(v))
                elif 'time' in k:
                    v = round(v / divider)
                    message += "`{}`\n".format(timedelta(seconds=v))
                elif 'elevation' in k:
                    v = round(v / divider)
                    message += "`{} m`\n".format(v)
                else:
                    v = round(v / divider, 1)
                    message += "`{}`\n".format(v)
            message += '\n'
    if not message:
        logger.warning(LOG_TEMPLATES['stats_none'].format(period, lang))
    else:
        logger.debug(LOG_TEMPLATES['stats_sent'].format(period, lang))
    return message


def activities(activities, lang='en'):
    if activities:
        logger.debug(LOG_TEMPLATES['activities_init'].format(lang))
        message = ''
        for activity in activities:
            activity_name = escape(activity.get('name').strip())
            activity_distance = escape(str(round(
                activity.get('distance') / 1000, 2)))
            activity_type = activity.get('type').lower()
            if lang != 'en':
                localed_activity = FORMATTER_TEMPLATES[lang]['types'].get(
                    activity_type)
                if localed_activity:
                    activity_type = localed_activity
            activity_id = activity.get('id')
            activity_date = timez_formatter(activity.get('start_date_local'))
            message += FORMATTER_TEMPLATES[lang]['acts']['date_name'].format(
                activity_date, activity_name)
            message += FORMATTER_TEMPLATES[lang]['acts']['type_dist'].format(
                distance=activity_distance, type=activity_type,
                id=activity_id)
            message += '\n'
        if not message:
            logger.warning(LOG_TEMPLATES['activities_none'].format(lang))
        else:
            logger.debug(LOG_TEMPLATES['activities_sent'].format(lang))
        return message


def activity(activity, lang='en'):
    if activity:
        logger.debug(LOG_TEMPLATES['activity_init'].format(lang))
        useful_data = ['start_date_local', 'name', 'description', 'id',
                       'distance', 'type', 'average_speed', 'max_speed',
                       'total_elevation_gain', 'moving_time', 'elapsed_time',
                       'device_name', 'gear', 'has_heartrate',
                       'average_heartrate', 'max_heartrate',
                       'elev_high', 'elev_low', 'average_watts',
                       'segment_efforts']
        activity_data = {k: activity.get(k) for k in useful_data}
        activity_type = activity_data.get('type').lower()
        id = activity_data.get('id')
        moving_time = activity_data.get('moving_time')
        elapsed_time = activity_data.get('elapsed_time')
        idle_time = elapsed_time - moving_time
        average_speed = activity_data.get('average_speed')
        maximum_speed = activity_data.get('max_speed')
        elevation = activity_data.get('total_elevation_gain')
        description = activity_data.get('description')
        gear = activity_data.get('gear')
        highest_elev = activity_data.get('elev_high')
        lowest_elev = activity_data.get('elev_low')
        average_watts = activity_data.get('average_watts')
        segment_efforts = activity_data.get('segment_efforts')
        if lang != 'en':
            localed_activity = FORMATTER_TEMPLATES[lang]['types'].get(
                activity_type)
            if localed_activity:
                activity_type = localed_activity
        if gear:
            gear_nickname = gear.get('nickname')
        else:
            gear_nickname = None
        device_name = activity_data.get('device_name')
        message = ''
        message += FORMATTER_TEMPLATES[lang]['act']['date_name'].format(
            timez_formatter(activity_data.get('start_date_local')),
            escape(activity_data.get('name').strip()))
        if description:
            message += '_{}_\n'.format(escape(description))
        message += FORMATTER_TEMPLATES[lang]['act']['dist_type_elev'].format(
            dist=distance_formatter(activity_data.get('distance')),
            type=activity_type, elev=escape(str(round(elevation))))
        if average_watts:
            message += FORMATTER_TEMPLATES[lang]['act']['avg_watts'].format(
                average_watts)
        if average_speed and maximum_speed:
            if activity_type in FORMATTER_TEMPLATES['pace_act']:
                message += FORMATTER_TEMPLATES[lang]['act']['pace'].format(
                    pace_formatter(average_speed),
                    pace_formatter(maximum_speed))
            else:
                message += FORMATTER_TEMPLATES[lang]['act']['speed'].format(
                    speed_formatter(average_speed),
                    speed_formatter(maximum_speed))
        if activity_data.get('has_heartrate'):
            average_heartrate = activity_data.get('average_heartrate')
            maximum_heartrate = activity_data.get('max_heartrate')
            message += FORMATTER_TEMPLATES[lang]['act']['hr'].format(
                average_heartrate, maximum_heartrate)
        message += FORMATTER_TEMPLATES[lang]['act']['time'].format(
            timedelta(seconds=moving_time), timedelta(seconds=elapsed_time))
        message += FORMATTER_TEMPLATES[lang]['act']['idle'].format(
            timedelta(seconds=idle_time),
            escape(str(round((idle_time / elapsed_time) * 100, 2))))
        if highest_elev and lowest_elev:
            message += FORMATTER_TEMPLATES[lang]['act']['elev'].format(
                highest_elev, lowest_elev)
        if device_name:
            message += FORMATTER_TEMPLATES[lang]['act']['device'].format(
                escape(device_name))
        if gear_nickname:
            message += FORMATTER_TEMPLATES[lang]['act']['gear'].format(
                escape(gear_nickname))
        message += FORMATTER_TEMPLATES[lang]['act']['strava_url'].format(
            FORMATTER_URLS['activity_url'], id)
        if segment_efforts:
            message += FORMATTER_TEMPLATES[lang]['act']['segment_list']
            for segment in segment_efforts:
                segment_name = segment['segment'].get('name')
                segment_id = segment['segment'].get('id')
                message += FORMATTER_TEMPLATES[lang]['act']['segment'].format(
                    segment_name, segment_id)
        message += FORMATTER_TEMPLATES[lang]['act']['dl'].format(id)
        if not message:
            logger.warning(LOG_TEMPLATES['activities_none'].format(lang))
        else:
            logger.debug(LOG_TEMPLATES['activities_sent'].format(lang))
        return message


def segment(segment, lang='en'):
    if segment:
        logger.debug(LOG_TEMPLATES['segment_init'].format(lang))
        useful_data = ['id' , 'name', 'activity_type', 'distance',
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
        if not message:
            logger.warning(LOG_TEMPLATES['segment_none'].format(lang))
        else:
            logger.debug(LOG_TEMPLATES['segment_sent'].format(lang))
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


def format_users(users):
    message = '`List of users in the database:`\n\n'
    for user in users:
        id = user[0]
        message += '[{}]({}{}) '.format(
            id, FORMATTER_URLS['user_profile_url'], id)
    return message
