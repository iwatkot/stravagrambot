from datetime import datetime

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from decouple import config
from log_handler import Logger, LogTemplates

logger = Logger(__name__)
Base = declarative_base()


class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)
    strava_id = Column(Integer)
    token_type = Column(String)
    access_token = Column(String)
    expires_at = Column(Integer)
    refresh_token = Column(String)

    def __repr__(self):
        return f"<User(id='{self.id}', telegram_id='{self.telegram_id}', "\
            f"strava_id='{self.strava_id}')>"


class DatabaseSession:
    def __init__(self, telegram_id):
        self.connection_config = {
            'user': config('DBUSER'),
            'password': config('PASSWORD'),
            'host': config('HOST'),
            'port': config('PORT'),
            'database': config('DATABASE'),
            'sslmode': 'require'}

        self.engine = create_engine('postgresql://',
                                    connect_args=self.connection_config)
        self.telegram_id = telegram_id

        self.connect()
        if self.session:
            logger.debug(LogTemplates[__name__].CONNECTED.format(
                self.telegram_id))
        else:
            logger.error(LogTemplates[__name__].CANT_CONNECT)

        self.user = None
        if self.exists_in_database():
            self.user = self.session.query(Users).filter(
                Users.telegram_id == self.telegram_id).one()
            self.strava_id = self.user.strava_id

    def connect(self):
        try:
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
        except Exception as error:
            logger.error(LogTemplates[__name__].CONNECTION_ERROR.format(
                error))

    def disconnect(self):
        self.session.close()
        logger.debug(LogTemplates[__name__].DISCONNECTED.format(
            self.telegram_id))

    def exists_in_database(self):
        return self.session.query(Users).filter(
            Users.telegram_id == self.telegram_id).count() > 0

    def token_expired(self):
        now = datetime.now().timestamp()
        return now > self.user.expires_at - (60 * 60)

    def get_token(self):
        return self.user.refresh_token if self.token_expired() else \
            self.user.access_token

    def get_users(self):
        return [user[0] for user in self.session.query(
            Users.strava_id).order_by(Users.id).all()]

    def add_user(self, auth_data):
        if self.exists_in_database():
            self.session.query(Users).filter(
                Users.telegram_id == self.telegram_id).delete()
            self.session.commit()
            logger.info(LogTemplates[__name__].DELETED_FROM_DATABASE.format(
                self.telegram_id))
        new_user = Users(**auth_data)
        self.session.add(new_user)
        self.session.commit()
        logger.info(LogTemplates[__name__].ADDED_TO_DATABASE.format(
            self.telegram_id))

    def update_user(self, auth_data):
        self.session.query(Users).filter_by(
            telegram_id=self.telegram_id).update(auth_data)
        self.session.commit()
