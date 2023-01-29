import requests

from decouple import config

from format_handler import get_template
from log_handler import Logger

OAUTH_URLS = get_template('url_templates')['oauth']
LOG_TEMPLATES = get_template('log_templates')['token_handler']
logger = Logger(__name__)


class Token():
    def __init__(self, telegram_id, code=None, refresh_token=None):
        self.client_id = config('CLIENT_ID')
        self.client_secret = config('CLIENT_SECRET')
        self.telegram_id = telegram_id
        self.refresh_token = refresh_token
        self.code = code

    def exchange(self):
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
        raw_response = requests.post(OAUTH_URLS['strava_oauth'], data=data)
        if raw_response.status_code == 200:
            response = raw_response.json()
            logger.info(LOG_TEMPLATES['RESPONSE_FROM_API'].format(
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
            logger.error(LOG_TEMPLATES['BAD_RESPONSE_FROM_API'].format(
                self.telegram_id))
