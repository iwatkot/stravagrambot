import os
import requests
import gpxpy.gpx

import pandas as pd


from datetime import datetime, timedelta

from format_handler import get_template
from database_handler import DataBase
from token_handler import Token
from log_handler import Logger

API_URLS = get_template('url_templates')['API']
LOG_TEMPLATES = get_template('log_templates')['api']
logger = Logger(__name__)

absolute_path = os.path.dirname(__file__)
try:
    os.mkdir(os.path.join(absolute_path, 'gpx'))
    logger.debug(LOG_TEMPLATES['GPX_DIR_CREATED'])
except FileExistsError:
    logger.debug(LOG_TEMPLATES['GPX_ALREADY_EXISTS'])


class APICaller:
    def __init__(self, telegram_id):
        self.telegram_id = telegram_id
        logger.debug(LOG_TEMPLATES['INIT'].format(self.telegram_id))
        self.get_access_token()
        if not self.access_token:
            logger.error(LOG_TEMPLATES['NO_TOKEN'].format(self.telegram_id))
            return None
        self.headers = {'Authorization': 'Bearer {}'.format(self.access_token)}

    def get_access_token(self):
        token_session = DataBase(telegram_id=self.telegram_id)
        if token_session.in_database():
            self.strava_id = token_session.get_strava_id()
            token_expired = token_session.token_expired()
            if token_expired:
                refresh_token = token_session.get_token('refresh_token')
                token = Token(self.telegram_id, refresh_token=refresh_token)
                auth_data = token.exchange()
                if auth_data:
                    update_session = DataBase(auth_data=auth_data)
                    update_session.update_data()
                    update_session.disconnect()
                else:
                    logger.error(LOG_TEMPLATES['UPDATE_TOCKEN_FAILED'].format(
                        self.telegram_id))
                    return None
            access_token = token_session.get_token('access_token')
            token_session.disconnect()
            logger.debug(LOG_TEMPLATES['TOKEN_RETRIEVED'].format(self.telegram_id))
            self.access_token = access_token
        else:
            self.access_token = None

    def get_stats(self):
        url = API_URLS['get_stats'].format(self.strava_id)
        logger.debug(LOG_TEMPLATES['GET_STATS'].format(self.telegram_id))
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            logger.debug(LOG_TEMPLATES['GOOD_RESPONSE'].format(
                self.telegram_id))
            return response.json()
        else:
            logger.error(LOG_TEMPLATES['BAD_RESPONSE'].format(
                self.telegram_id))
            return None

    def activities(self, after=None, before=None):
        url = API_URLS['activities']
        logger.debug(LOG_TEMPLATES['ACTIVITIES'].format(self.telegram_id))
        if not after and not before:
            before = int(datetime.now().timestamp())
            after = before - (90 * 24 * 60 * 60)
        params = {
            'before': before,
            'after': after,
            'page': '1',
            'per_page': '180'}
        response = requests.get(url, params=params, headers=self.headers)
        if response.status_code == 200:
            logger.debug(LOG_TEMPLATES['GOOD_RESPONSE'].format(
                self.telegram_id))
            return response.json()[::-1]
        else:
            logger.error(LOG_TEMPLATES['BAD_RESPONSE'].format(
                self.telegram_id))
            return None

    def activity(self, activity_id):
        self.activity_id = activity_id
        url = API_URLS['activity'].format(activity_id)
        logger.debug(LOG_TEMPLATES['ACTIVITY'].format(self.telegram_id))
        params = {'include_all_efforts': 'False'}
        response = requests.get(url, params=params, headers=self.headers)
        if response.status_code == 200:
            logger.debug(LOG_TEMPLATES['GOOD_RESPONSE'].format(
                self.telegram_id))
            activity_data = response.json()
            self.start_time = activity_data.get('start_date_local')
            return activity_data
        else:
            logger.error(LOG_TEMPLATES['BAD_RESPONSE'].format(
                self.telegram_id))
            self.start_time = None
            return None

    def create_gpx(self):
        logger.debug(LOG_TEMPLATES['GPX_STARTED'].format(self.activity_id))
        url = API_URLS['streams'].format(self.activity_id)
        try:
            latlong = requests.get(
                url, headers=self.headers,
                params={'keys': ['latlng']}).json()[0]['data']
            time_list = requests.get(
                url, headers=self.headers,
                params={'keys': ['time']}).json()[1]['data']
            altitude = requests.get(
                url, headers=self.headers,
                params={'keys': ['altitude']}).json()[1]['data']
        except Exception:
            logger.error(LOG_TEMPLATES['GPX_RETRIEVE_ERROR'].format(
                self.activity_id))
            return None
        data = pd.DataFrame([*latlong], columns=['lat', 'long'])
        data['altitude'] = altitude
        start = datetime.strptime(self.start_time, "%Y-%m-%dT%H:%M:%SZ")
        data['time'] = [(start+timedelta(seconds=t)) for t in time_list]
        gpx = gpxpy.gpx.GPX()
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        for idx in data.index:
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(
                                      data.loc[idx, 'lat'],
                                      data.loc[idx, 'long'],
                                      elevation=data.loc[idx, 'altitude'],
                                      time=data.loc[idx, 'time']))
        filepath = os.path.join(
            absolute_path, 'gpx/{}.gpx'.format(self.activity_id))
        with open(filepath, 'w') as gpxf:
            gpxf.write(gpx.to_xml())
        logger.info(LOG_TEMPLATES['GPX_CREATED'].format(filepath))
        return filepath
