import psycopg2

from decouple import config
from psycopg2 import Error
from datetime import datetime

from format_handler import get_template
from log_handler import Logger

QUERY_TEMPLATES = get_template('query_templates')
LOG_TEMPLATES = get_template('log_templates')['database_handler']
logger = Logger(__name__)


class DataBase:
    def __init__(self, auth_data=None, telegram_id=None):
        self.user = config('PUSER')
        self.password = config('PASSWORD')
        self.host = config('HOST')
        self.port = config('PORT')
        self.ssl_mode = 'require'
        self.database = config('DATABASE')
        self.auth_data = auth_data
        self.telegram_id = telegram_id
        if not self.telegram_id:
            self.telegram_id = self.auth_data['telegram_id']
            logger.debug(LOG_TEMPLATES['DB_INIT_AUTH_DATA'].format(
                self.telegram_id))
        else:
            logger.debug(LOG_TEMPLATES['DB_INIT_TELEGRAM_ID'].format(
                self.telegram_id))
        self.connect()
        if not self.connection:
            logger.error(LOG_TEMPLATES['CANT_CONNECT'])
            return None

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                sslmode=self.ssl_mode,
                database=self.database)
            logger.debug(LOG_TEMPLATES['CONNECTED'].format(self.telegram_id))
        except (Exception, Error) as error:
            logger.error(error)
            self.connection = None

    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.debug(LOG_TEMPLATES['DISCONNECTED'].format(
                self.telegram_id))
        else:
            logger.warning(LOG_TEMPLATES['NO_CONNECTION'])

    def in_database(self):
        cursor = self.connection.cursor()
        check_query = QUERY_TEMPLATES['check_query'].format(self.telegram_id)
        cursor.execute(check_query)
        db_response = cursor.fetchone()[0]
        if db_response:
            logger.debug(LOG_TEMPLATES['IN_DATABASE'].format(self.telegram_id))
        else:
            logger.debug(LOG_TEMPLATES['NOT_IN_DATABASE'].format(
                self.telegram_id))
        cursor.close()
        return db_response

    def modify_data(self, action=None):
        cursor = self.connection.cursor()
        if action == 'update':
            delete_query = QUERY_TEMPLATES['delete_query'].format(
                self.telegram_id)
            logger.info(LOG_TEMPLATES['DELETED_FROM_DATABASE'].format(
                self.telegram_id))
            cursor.execute(delete_query)
            self.connection.commit()
        insert_query = QUERY_TEMPLATES['insert_query'].format(
            *self.auth_data.values())
        logger.info(LOG_TEMPLATES['ADDED_TO_DATABASE'].format(
            self.telegram_id))
        cursor.execute(insert_query)
        self.connection.commit()
        cursor.close()

    def update_data(self):
        cursor = self.connection.cursor()
        update_query = QUERY_TEMPLATES['update_query'].format(
            self.auth_data['token_type'], self.auth_data['access_token'],
            self.auth_data['expires_at'], self.auth_data['refresh_token'],
            self.telegram_id)
        cursor.execute(update_query)
        logger.info(LOG_TEMPLATES['TOKEN_REFRESHED'].format(self.telegram_id))
        self.connection.commit()
        cursor.close()

    def token_expired(self):
        cursor = self.connection.cursor()
        expires_at_query = QUERY_TEMPLATES['expires_at_query'].format(
            self.telegram_id)
        cursor.execute(expires_at_query)
        db_response = cursor.fetchone()[0]
        now = datetime.now().timestamp()
        cursor.close()
        expired = now > db_response - (60 * 60)
        if expired:
            logger.info(LOG_TEMPLATES['TOKEN_EXPIRED'].format(
                self.telegram_id))
        else:
            logger.debug(LOG_TEMPLATES['TOKEN_NOT_EXPIRED'].format(
                self.telegram_id))
        return expired

    def get_token(self, token_type):
        logger.debug(LOG_TEMPLATES['GETTING_TOKEN'].format(
            token_type, self.telegram_id))
        cursor = self.connection.cursor()
        get_token_query = QUERY_TEMPLATES['get_token_query'].format(
            token_type, self.telegram_id)
        cursor.execute(get_token_query)
        db_response = cursor.fetchone()[0]
        cursor.close()
        return db_response

    def get_strava_id(self):
        logger.debug(LOG_TEMPLATES['GETTING_STRAVA_ID'].format(
            self.telegram_id))
        cursor = self.connection.cursor()
        get_strava_id_query = QUERY_TEMPLATES['get_strava_id_query'].format(
            self.telegram_id)
        cursor.execute(get_strava_id_query)
        strava_id = cursor.fetchone()[0]
        cursor.close()
        return strava_id

    def get_users(self):
        logger.debug(LOG_TEMPLATES['GETTING_USERS'])
        cursor = self.connection.cursor()
        get_users_query = QUERY_TEMPLATES['get_users']
        cursor.execute(get_users_query)
        users = cursor.fetchall()
        cursor.close()
        return users
