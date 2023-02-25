import os
import requests
import gpxpy.gpx

import pandas as pd

from datetime import datetime, timedelta

from database_handler import DatabaseSession
from token_handler import Token
from log_handler import Logger, LogTemplates
from templates_handler import Urls, Constants

logger = Logger(__name__)


class APICaller:
    """Making calls to the Strava API, uses connections from the
    DataBase class and token exchange procedures from the Token class."""
    def __init__(self, telegram_id: int):
        self.telegram_id = telegram_id
        logger.debug(LogTemplates[__name__].INIT.format(self.telegram_id))
        self.get_access_token()
        if not self.access_token:
            logger.error(LogTemplates[__name__].NO_TOKEN.format(
                self.telegram_id))
        self.headers = {'Authorization': 'Bearer {}'.format(self.access_token)}

    def get_access_token(self) -> None:
        """Getting access token from the database.
        If token expired launches the token exchange procedure
        and updates token in the database."""
        token_session = DatabaseSession(self.telegram_id)
        self.strava_id = token_session.strava_id
        if token_session.token_expired():
            refresh_token = token_session.get_token()
            token = Token(self.telegram_id, refresh_token=refresh_token)
            auth_data = token.exchange()
            if auth_data:
                update_session = DatabaseSession(self.telegram_id)
                update_session.update_user(auth_data)
                update_session.disconnect()
            else:
                logger.error(
                    LogTemplates[__name__].UPDATE_TOCKEN_FAILED.format(
                        self.telegram_id))
                return
        self.access_token = token_session.get_token()
        token_session.disconnect()

    def get_stats(self) -> dict:
        """Makes call to the API to recieve athlete's stats."""
        url = Urls.GET_STATS.format(self.strava_id)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()

    def raw_data(self, **kwargs) -> dict:
        """Making simple API calls and returns dict with raw data."""
        url = Urls[list(kwargs.keys())[0]].format(*kwargs.values())
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()

    def get_activities(self, after: int = None, before: int = None) -> list:
        """Returns the list of the activities
        in the specified period of time"""
        url = Urls.GET_ACTIVITIES
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
        logger.debug(LogTemplates[__name__].GPX_STARTED.format(activity_id))
        start_time = self.raw_data(
            get_activity=activity_id).get('start_date_local')
        url = Urls.CREATE_GPX.format(activity_id)
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
            logger.error(LogTemplates[__name__].GPX_RETRIEVE_ERROR.format(
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
            Constants.ABSOLUTE_PATH.value, 'gpx/{}.gpx'.format(activity_id))
        with open(filepath, 'w') as gpxf:
            gpxf.write(gpx.to_xml())
        logger.info(LogTemplates[__name__].GPX_CREATED.format(filepath))
        return filepath
