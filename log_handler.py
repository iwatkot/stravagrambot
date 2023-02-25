import logging
import os
import sys
import json

from pydantic import BaseModel

absolute_path = os.path.dirname(__file__)
os.makedirs(os.path.join(absolute_path, 'logs'), exist_ok=True)
LOG_FORMATTER = "%(name)s | %(asctime)s | %(levelname)s | %(message)s"
LOG_FILE = os.path.join(absolute_path, 'logs/main_log.txt')
LOG_TEMPLATES_FILE = os.path.join(absolute_path,
                                  'templates/log_templates.json')


class DatabaseHandlerModel(BaseModel):
    CONNECTED: str
    CANT_CONNECT: str
    CONNECTION_ERROR: str
    DISCONNECTED: str
    DELETED_FROM_DATABASE: str
    ADDED_TO_DATABASE: str


class FlaskServerModel(BaseModel):
    SERVER_STARTED: str
    SERVER_STOPPED: str
    GET_REQUEST: str
    PARSED_DATA: str
    BAD_REQUEST: str
    GOOD_REQUEST: str
    OAUTH_FAILED: str
    NOT_CONNECTED: str
    RETURNING_HUB_CHALLENGE: str
    WEBHOOK_RECIEVED: str


class TokenHandlerModel(BaseModel):
    GOOD_RESPONSE_FROM_API: str
    BAD_RESPONSE_FROM_API: str


class WebhookHandlerModel(BaseModel):
    SUBSCRIBE_REQUESTED: str
    VIEW_REQUESTED: str
    DELETE_REQUESTED: str
    SUB_DELETED: str
    API_RESPONDED: str
    SUBSCRIPTION_ID: str
    BAD_RESPONSE: str
    CANT_UNPACK: str
    NO_SUB_TO_DELETE: str


class ApiHandlerModel(BaseModel):
    UPDATE_TOCKEN_FAILED: str
    INIT: str
    NO_TOKEN: str
    GPX_STARTED: str
    GPX_RETRIEVE_ERROR: str
    GPX_CREATED: str


class FormatHandlerModel(BaseModel):
    FUNCTION_INIT: str


class BotModel(BaseModel):
    LOG_MESSAGE: str
    LOG_CALLBACK: str


class AllTemplates(BaseModel):
    database_handler: DatabaseHandlerModel
    flask_server: FlaskServerModel
    token_handler: TokenHandlerModel
    webhook_handler: WebhookHandlerModel
    api_handler: ApiHandlerModel
    format_handler: FormatHandlerModel
    bot: BotModel

    def __getitem__(self, key):
        return getattr(self, key)


LogTemplates = AllTemplates.parse_obj(json.load(open(LOG_TEMPLATES_FILE)))


class Logger(logging.getLoggerClass()):
    """Handles logging to the file and stroudt with timestamps."""
    def __init__(self, name: str):
        super().__init__(name)
        self.setLevel(logging.DEBUG)
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.file_handler = logging.FileHandler(
            filename=LOG_FILE, mode='a')
        self.fmt = LOG_FORMATTER
        self.stdout_handler.setFormatter(logging.Formatter(LOG_FORMATTER))
        self.file_handler.setFormatter(logging.Formatter(LOG_FORMATTER))
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)


def get_log_file() -> str:
    """Returns the path to the main_log file."""
    return LOG_FILE
