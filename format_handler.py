import os
import json

from re import escape
from datetime import timedelta, datetime

absolute_path = os.path.dirname(__file__)


def get_template(file):
    filepath = os.path.join(absolute_path, 'templates/{}.json'.format(file))
    return json.load(open(filepath, encoding='utf-8'))


FORMATTER_URLS = get_template('url_templates')['formatter']
FORMATTER_TEMPLATES = get_template('formatter_templates')


def stats(stats, period='all', lang='en'):
    if period == 'week':
        data_dict = FORMATTER_TEMPLATES[lang]['weekavg']
        today = datetime.date(datetime.now())
        divider = today.isocalendar().week
    else:
        data_dict = FORMATTER_TEMPLATES[lang]['stats']
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
            message = 'You have no actual data in your Strava account\\.'
    return message


def activities(activities):
    if activities:
        message = ''
        for activity in activities:
            act_name = escape(activity.get('name').strip())
            act_distance = escape(str(round(
                activity.get('distance') / 1000, 2)))
            act_type = activity.get('type').lower()
            act_id = activity.get('id')
            act_date = timez_formatter(activity.get('start_date_local'))
            message += "*{}* \\| `{}`\n".format(act_date, act_name)
            message += "{} km {} \\| more data: /activity{}\n".format(
                act_distance, act_type, act_id)
            message += '\n'
        return message


def activity(activity, lang='en'):
    if activity:
        useful_data = ['start_date_local', 'name', 'description', 'id',
                       'distance', 'type', 'average_speed', 'max_speed',
                       'total_elevation_gain', 'moving_time', 'elapsed_time',
                       'device_name', 'gear', 'has_heartrate',
                       'average_heartrate', 'max_heartrate',
                       'elev_high', 'elev_low']
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
        message += FORMATTER_TEMPLATES[lang]['act']['dl'].format(id)
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
    message = '`List of the in the database:`\n\n'
    for user in users:
        id = user[0]
        message += '[{}]({}{}) '.format(
            id, FORMATTER_URLS['user_profile_url'], id)
    return message
