import os

from enum import Enum


class Urls(Enum):
    GET_STATS = "https://www.strava.com/api/v3/athletes/{}/stats"
    GET_ACTIVITIES = "https://www.strava.com/api/v3/athlete/activities"
    CREATE_GPX = "https://www.strava.com/api/v3/activities/{}/streams"
    OAUTH_URL = "http://www.strava.com/oauth/authorize?client_id=13782&"\
        "response_type=code&redirect_uri=http://stravagram.space/"\
        "stravagramoauth?telegram_id={}&exchange_token&approval_prompt="\
        "force&scope=read_all,activity:read_all"
    get_activity = "https://www.strava.com/api/v3/activities/{}"
    get_segment = "https://www.strava.com/api/v3/segments/{}"
    get_starred_segments = "https://www.strava.com/api/v3/segments/starred"
    get_gear = "https://www.strava.com/api/v3/gear/{}"

    def format(self, *args):
        return self.value.format(*args)

    def __str__(self):
        return f"{self.value}"


class Constants(Enum):
    ABSOLUTE_PATH = os.path.dirname(__file__)
    DIRS = ['logs', 'gpx', 'images']
    SUPPORTED_LANGUAGES = ["en", "ru"]


def startup():
    for d in Constants.DIRS.value:
        os.makedirs(os.path.join(Constants.ABSOLUTE_PATH.value, d),
                    exist_ok=True)
