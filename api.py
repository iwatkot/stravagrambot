import requests

from templates_handler import get_template
from database_handler import DataBase
from token_handler import Token
from log_handler import Logger

API_URLS = get_template('url_templates')['API']
LOG_TEMPLATES = get_template('log_templates')['api']
logger = Logger(__name__)


class APICaller:
    def __init__(self, telegram_id):
        self.telegram_id = telegram_id
        logger.debug(LOG_TEMPLATES['INIT'].format(self.telegram_id))
        self.get_access_token()
        if not self.access_token:
            logger.error(LOG_TEMPLATES['NO_TOKEN'].format(self.telegram_id))
            return None

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
            self.access_token = access_token
        else:
            self.access_token = None

    def get_stats(self):
        url = API_URLS['get_stats'].format(self.strava_id)
        headers = {
            'Authorization': 'Bearer {}'.format(self.access_token)
        }
        logger.debug(LOG_TEMPLATES['GET_STATS'].format(self.telegram_id))
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            logger.debug(LOG_TEMPLATES['GOOD_RESPONSE'].format(
                self.telegram_id))
            return response.json()
        else:
            logger.error(LOG_TEMPLATES['BAD_RESPONSE'].format(
                self.telegram_id))
            return None
