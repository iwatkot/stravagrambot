import requests

from decouple import config
from log_handler import Logger
from format_handler import get_template

LOG_TEMPLATES = get_template('log_templates')['webhook_handler']
logger = Logger(__name__)


class WebHook:
    """Handles Strava webhook service subscription. Uses methods to
    subscrive, view or delete active webhook subscription."""
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

    def subscribe(self) -> int | None:
        """Initiates a new webhook subscription. Returns id or None."""
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
            try:
                self.subcription_id = response['id']
                logger.debug(LOG_TEMPLATES['SUBSCRIPTION_ID'].format(
                    self.subcription_id))
            except Exception as error:
                logger.error(LOG_TEMPLATES['CANT_UNPACK'].format(error))
        else:
            logger.warning(LOG_TEMPLATES['BAD_RESPONSE'].format(
                response.json()))
        return self.subcription_id

    def view(self) -> int | None:
        """Making request to check if the active subscription is exists.
        Returns subscription id or None."""
        logger.debug(LOG_TEMPLATES['VIEW_REQUESTED'])
        response = requests.get(self.api_url, params=self.params)
        if response.status_code == 200:
            response = response.json()
            try:
                self.subcription_id = response[0]['id']
                logger.debug(LOG_TEMPLATES['SUBSCRIPTION_ID'].format(
                    self.subcription_id))
            except Exception as error:
                logger.error(LOG_TEMPLATES['CANT_UNPACK'].format(error))
        else:
            logger.warning(LOG_TEMPLATES['BAD_RESPONSE'].format(
                response.json()))
            self.subcription_id = None
        return self.subcription_id

    def delete(self) -> bool:
        """Initiates webhook subscription deleting. Returns bool depending
        of request result."""
        self.view()
        logger.debug(LOG_TEMPLATES['DELETE_REQUESTED'])
        response = requests.delete(self.api_url + '/{}'.format(
            self.subcription_id), params=self.params)
        if response.status_code == 204:
            logger.debug(LOG_TEMPLATES['SUB_DELETED'])
            return True
        else:
            logger.error(LOG_TEMPLATES['NO_SUB_TO_DELETE'])
            return False
