import requests

from decouple import config

from log_handler import Logger, LogTemplates
from format_handler import Urls

logger = Logger(__name__)


class Token():
    """Handles token exchange procedure with Strava API."""
    def __init__(self, telegram_id: int,
                 code: str = None, refresh_token: str = None):
        self.client_id = config('CLIENT_ID')
        self.client_secret = config('CLIENT_SECRET')
        self.telegram_id = telegram_id
        self.refresh_token = refresh_token
        self.code = code

    def exchange(self) -> None:
        """Exchange tokens (code or refresh token for access token) and
        writes it into the database."""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        if self.refresh_token:
            data['grant_type'] = 'refresh_token'
            data['refresh_token'] = self.refresh_token
        else:
            data['code'] = self.code
            data['grant_type'] = 'authorization_code'
        raw_response = requests.post(Urls.STRAVA_API, data=data)
        if raw_response.status_code == 200:
            response = raw_response.json()
            logger.info(LogTemplates[__name__].GOOD_RESPONSE_FROM_API.format(
                self.telegram_id))
            auth_data = {
                "telegram_id": self.telegram_id,
            }
            if self.code:
                auth_data.update({"strava_id": response['athlete']['id']})
            auth_data.update({
                "token_type": response['token_type'],
                "access_token": response['access_token'],
                "expires_at": response['expires_at'],
                "refresh_token": response['refresh_token']})
            return auth_data
        else:
            logger.error(LogTemplates[__name__].BAD_RESPONSE_FROM_API.format(
                self.telegram_id))
