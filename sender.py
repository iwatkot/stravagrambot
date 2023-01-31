import format_handler as formatter

from database_handler import DataBase
from api import APICaller
from bot import send_update
from log_handler import Logger

logger = Logger(__name__)


def handle_webhook(webhook: dict):
    """Checks webhook data, making API call, formatts activity data and
    send it to the user."""
    if webhook.get('aspect_type') == 'create' and webhook.get(
                   'object_type') == 'activity':
        logger.debug('Sender initiated')
        strava_id = webhook.get('owner_id')
        activity_id = webhook.get('object_id')
        tg_session = DataBase(strava_id=strava_id)
        telegram_id = tg_session.get_id(strava_id)
        lang = tg_session.get_lang()
        tg_session.disconnect()
        caller = APICaller(telegram_id)
        raw_data = caller.raw_data(get_activity=activity_id)
        message = formatter.format_activity(raw_data, lang)
        send_update(telegram_id, message)
