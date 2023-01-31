import os
import requests
import gpxpy.gpx

import pandas as pd

from enum import Enum
from datetime import datetime, timedelta

from format_handler import get_template
from database_handler import DataBase
from token_handler import Token
from log_handler import Logger

LOG_TEMPLATES = get_template('log_templates')['api']
logger = Logger(__name__)

absolute_path = os.path.dirname(__file__)
os.makedirs(os.path.join(absolute_path, 'gpx'), exist_ok=True)


class Urls(Enum):
    GET_STATS = "https://www.strava.com/api/v3/athletes/{}/stats"
    GET_ACTIVITIES = "https://www.strava.com/api/v3/athlete/activities"
    get_activity = "https://www.strava.com/api/v3/activities/{}"
    CREATE_GPX = "https://www.strava.com/api/v3/activities/{}/streams"
    get_segment = "https://www.strava.com/api/v3/segments/{}"
    get_starred_segments = "https://www.strava.com/api/v3/segments/starred"
    get_gear = "https://www.strava.com/api/v3/gear/{}"


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
            self.strava_id = token_session.get_id()
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
        url = Urls.GET_STATS.value.format(self.strava_id)
        print(url)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()

    def raw_data(self, **kwargs) -> dict:
        """Making simple API calls and returns dict with raw data."""
        url = Urls[list(kwargs.keys())[0]].value.format(*kwargs.values())
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()

    def get_activities(self, after: int = None, before: int = None) -> list:
        """Returns the list of the activities
        in the specified period of time"""
        url = Urls.GET_ACTIVITIES.value
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

    def create_gpx(self, activity_id: int) -> str:
        """Creates GPX files from API streams request,
        returns the path to the file."""
        logger.debug(LOG_TEMPLATES['GPX_STARTED'].format(activity_id))
        start_time = self.raw_data(
            get_activity=activity_id).get('start_date_local')
        url = Urls.CREATE_GPX.value.format(activity_id)
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
                activity_id))
            return None

        data = pd.DataFrame([*latlong], columns=['lat', 'long'])
        data['altitude'] = altitude
        start = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
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
            absolute_path, 'gpx/{}.gpx'.format(activity_id))
        with open(filepath, 'w') as gpxf:
            gpxf.write(gpx.to_xml())
        logger.info(LOG_TEMPLATES['GPX_CREATED'].format(filepath))
        return filepath
