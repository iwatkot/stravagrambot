import requests

from decouple import config
from log_handler import Logger
from format_handler import get_template

LOG_TEMPLATES = get_template('log_templates')['webhook_handler']
logger = Logger(__name__)


class WebHook:
    def __init__(self):
        self.client_id = config('CLIENT_ID')
        self.client_secret = config('CLIENT_SECRET')
        self.callback_url = config('CALLBACK_URL')
        self.verify_token = config('VERIFY_TOKEN')
        self.api_url = config('API_URL')
        self.params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        self.subcription_id = None

    def subscribe(self):
        data = self.params
        data.update({
            'callback_url': self.callback_url,
            'verify_token': self.verify_token,
        })
        logger.debug(LOG_TEMPLATES['SUBSCRIBE_REQUESTED'])
        response = requests.post(self.api_url, data=data)
        if response.status_code == 201:
            response = response.json()
            logger.debug(LOG_TEMPLATES['API_RESPONDED'].format(response))
            self.subcription_id = response['id']
            logger.debug(LOG_TEMPLATES['SUBSCRIPTION_ID'].format(
                self.subcription_id))
        else:
            logger.warning(LOG_TEMPLATES['BAD_RESPONSE'].format(
                response.json()))
            self.subcription_id = None

    def view(self):
        logger.debug(LOG_TEMPLATES['VIEW_REQUESTED'])
        response = requests.get(self.api_url, params=self.params)
        if response.status_code == 200:
            response = response.json()
            self.subcription_id = response[0]['id']
            logger.debug(LOG_TEMPLATES['SUBSCRIPTION_ID'].format(
                self.subcription_id))
        else:
            logger.warning(LOG_TEMPLATES['BAD_RESPONSE'].format(
                response.json()))
            self.subcription_id = None

    def delete(self):
        logger.debug(LOG_TEMPLATES['DELETE_REQUESTED'])
        response = requests.delete(self.api_url + '/{}'.format(
            self.subcription_id), params=self.params).status_code
        if response == 204:
            logger.debug(LOG_TEMPLATES['SUB_DELETED'])
