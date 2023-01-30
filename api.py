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
os.makedirs(os.path.join(absolute_path, 'gpx'), exist_ok=True)


class APICaller:
    """Making calls to the Strava API, uses connections from the
    DataBase class and token exchange procedures from the Token class."""
    def __init__(self, telegram_id: int):
        self.telegram_id = telegram_id
        logger.debug(LOG_TEMPLATES['INIT'].format(self.telegram_id))
        self.get_access_token()
        if not self.access_token:
            logger.error(LOG_TEMPLATES['NO_TOKEN'].format(self.telegram_id))
            return None
        self.headers = {'Authorization': 'Bearer {}'.format(self.access_token)}

    def get_access_token(self) -> None:
        """Getting access token from the database.
        If token expired launches the token exchange procedure
        and updates token in the database."""
        token_session = DataBase(telegram_id=self.telegram_id)
        if token_session.in_database():
            self.strava_id = token_session.get_strava_id()
            token_expired = token_session.token_expired()
            if token_expired:
                # Launching refresh token procedure, if it's expired.
                refresh_token = token_session.get_token('refresh_token')
                token = Token(self.telegram_id, refresh_token=refresh_token)
                auth_data = token.exchange()
                if auth_data:
                    # Updating database entry with new keys.
                    update_session = DataBase(self.telegram_id, auth_data)
                    update_session.update_data()
                    update_session.disconnect()
                else:
                    logger.error(LOG_TEMPLATES['UPDATE_TOCKEN_FAILED'].format(
                        self.telegram_id))
                    return None
            # Using the access token from the database, if it's not expired.
            access_token = token_session.get_token('access_token')
            token_session.disconnect()
            self.access_token = access_token
        else:
            # If entry for specified telegram ID wasn't found in the database.
            token_session.disconnect()
            self.access_token = None

    def get_stats(self) -> dict:
        """Makes call to the API to recieve athlete's stats."""
        url = API_URLS['get_stats'].format(self.strava_id)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()

    def get_activities(self, after: int = None, before: int = None) -> list:
        """Returns the list of the activities
        in the specified period of time"""
        url = API_URLS['activities']
        # If period of time wasn't specified, using 60 days before now.
        if not after and not before:
            before = int(datetime.now().timestamp())
            after = before - (60 * 24 * 60 * 60)
        params = {
            'before': before,
            'after': after,
            'page': '1',
            'per_page': '180'}
        response = requests.get(url, params=params, headers=self.headers)
        if response.status_code == 200:
            return response.json()[::-1]

    def get_activity(self, activity_id: int) -> dict:
        """Returns dictionary with raw activity data."""
        self.activity_id = activity_id
        url = API_URLS['activity'].format(activity_id)
        params = {'include_all_efforts': 'False'}
        response = requests.get(url, params=params, headers=self.headers)
        if response.status_code == 200:
            activity = response.json()
            # Start time is needed for create_gpx() to avoid second API call.
            self.start_time = activity.get('start_date_local')
            return activity

    def create_gpx(self) -> str:
        """Creates GPX files from API streams request,
        returns the path to the file."""
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

    def get_segment(self, segment_id: int) -> dict:
        """Returns dictionary with raw segment data."""
        url = API_URLS['segment'].format(segment_id)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            segment = response.json()
            return segment

    def get_starred_segments(self) -> list:
        """Returns list with raw starred segments data."""
        url = API_URLS['starred_segments']
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()

    def get_gear(self, gear_id: int) -> dict:
        """Returns dictionary with raw gear data."""
        url = API_URLS['gear'].format(gear_id)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
