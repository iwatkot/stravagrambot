import os
import json

from re import escape
from datetime import timedelta, datetime

absolute_path = os.path.dirname(__file__)


def get_template(file):
    filepath = os.path.join(absolute_path, 'templates/{}.json'.format(file))
    return json.load(open(filepath, encoding='utf-8'))


FORMATTER_URLS = get_template('url_templates')['formatter']


def stats(stats, type):
    stat_dicts = {
        'all_ride_totals': "Ride overall stats",
        'all_run_totals': "Run overall stats",
        'ytd_ride_totals': "This year ride stats",
        'ytd_run_totals': "This year run stats"}
    if type == 'year':
        del stat_dicts['all_ride_totals']
        del stat_dicts['all_run_totals']
    message = ''
    for k, v in stat_dicts.items():
        stat_dict = stats.get(k)
        count = stat_dict.get('count')
        if count:
            message += '`{}`\n'.format(v)
            for k, v in stat_dict.items():
                message += "*{}*: ".format(k.replace('_', ' ').title())
                if 'distance' in k:
                    escaped_distance = escape(str(round(v / 1000, 2)))
                    message += "{} km\n".format(escaped_distance)
                elif 'time' in k:
                    time = timedelta(seconds=v)
                    message += "{}\n".format(time)
                elif 'elevation' in k:
                    message += "{} m\n".format(v)
                else:
                    message += "{}\n".format(v)
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


def activity(activity):
    if activity:
        useful_data = ['start_date_local', 'name', 'description', 'id',
                       'distance', 'type', 'average_speed', 'max_speed',
                       'total_elevation_gain', 'moving_time', 'elapsed_time',
                       'device_name', 'gear']
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
        if gear:
            gear_nickname = gear.get('nickname')
        else:
            gear_nickname = None
        device_name = activity_data.get('device_name')
        message = ''
        message += '*{}* \\| `{}`\n'.format(
            timez_formatter(activity_data.get('start_date_local')),
            escape(activity_data.get('name').strip()))
        if description:
            message += '_{}_\n'.format(escape(description))
        message += '`{} km`  {} with  `{} m`  elevation gained\n'.format(
            distance_formatter(activity_data.get('distance')),
            activity_type, escape(str(round(elevation))))
        if average_speed and maximum_speed:
            if activity_type == 'run':
                message += '*Average pace:*  `{}` \\| '.format(
                    pace_formatter(average_speed))
                message += '*Maximum pace:*  `{}`\n'.format(
                    pace_formatter(maximum_speed))
            else:
                message += '*Average speed:*  `{} km\\/h` \\| '.format(
                    speed_formatter(average_speed))
                message += '*Maximum speed:*  `{} km\\/h`\n'.format(
                    speed_formatter(maximum_speed))
        message += '*Moving time:*  `{}` \\| *Elapsed time:*  `{}`\n'.format(
            timedelta(seconds=moving_time), timedelta(seconds=elapsed_time))
        message += '*Idle time:*  `{}` \\| *Idle percent:*  `{} %`\n'.format(
            timedelta(seconds=idle_time),
            escape(str(round((idle_time / elapsed_time) * 100, 2))))
        if device_name:
            message += '*Workout recorded with:* {}\n'.format(
                escape(device_name))
        if gear_nickname:
            message += '*Gear:* {}\n'.format(escape(gear_nickname))
        message += '[Check activity on Strava]({}{})\n\n'.format(
            FORMATTER_URLS['activity_url'], id)
        message += '*Download GPX file:* /download{}'.format(id)
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
