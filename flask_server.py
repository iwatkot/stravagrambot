import json
import logging

from flask import Flask, request, render_template
from decouple import config

from format_handler import get_template
from database_handler import DataBase
from log_handler import Logger
from token_handler import Token

OAUTH_TEMPLATES = get_template('flask_templates')['oauth']
LOG_TEMPLATES = get_template('log_templates')['flask_server']
logger = Logger('flask_server')
flask_log = logging.getLogger('werkzeug')
flask_log.disabled = True

app = Flask(__name__)


@app.route(OAUTH_TEMPLATES['webhooks_marker'], methods=["GET"])
def webhook_challenge():
    logger.debug(LOG_TEMPLATES['GET_REQUEST'].format(request.full_path))
    verify_token = request.args.get('hub.verify_token')
    if verify_token == config('VERIFY_TOKEN'):
        hub_challenge = request.args.get('hub.challenge')
        logger.debug(LOG_TEMPLATES['RETURNING_HUB_CHALLENGE'].format(
            hub_challenge))
        return json.dumps({'hub.challenge': hub_challenge}), 200


@app.route(OAUTH_TEMPLATES['webhooks_marker'], methods=["POST"])
def webhook_catcher():
    if request.content_type == 'application/json':
        json_data = request.json
        object_type = json_data.get('object_type')
        object_id = json_data.get('object_id')
        owner_id = json_data.get('owner_id')
        updates = json_data.get('updates')
    print(object_type, object_id, owner_id, updates)
    return '', 200


@app.route(OAUTH_TEMPLATES['oauth_marker'])
def oauth():
    logger.debug(LOG_TEMPLATES['GET_REQUEST'].format(request.full_path))
    telegram_id = request.args.get('telegram_id')
    code = request.args.get('code')
    scope = request.args.get('scope')
    if 'activity:read_all' not in scope:
        logger.debug(LOG_TEMPLATES['BAD_REQUEST'].format(telegram_id))
        message = OAUTH_TEMPLATES['bad_request']
        result = 'Authentication failed'
    else:
        logger.debug(LOG_TEMPLATES['GOOD_REQUEST'].format(
                    telegram_id, code))
        oauth_init(telegram_id, code)
        message = OAUTH_TEMPLATES['good_request']
        result = 'Authentication successfull'
    return render_template('pages/oauth.html',
                           result=result, message=message)


def oauth_init(telegram_id, code):
    token = Token(telegram_id=telegram_id, code=code)
    auth_data = token.exchange()
    if auth_data:
        oauth_session = DataBase(auth_data=auth_data)
        if not oauth_session.connection:
            logger.error(LOG_TEMPLATES['NOT_CONNECTED'])
            return None
        if oauth_session.in_database():
            oauth_session.modify_data(action='update')
        else:
            oauth_session.modify_data()
        oauth_session.disconnect()
    else:
        logger.error(LOG_TEMPLATES['OAUTH_FAILED'])


if __name__ == '__main__':
    port = 80
    logger.info(LOG_TEMPLATES['SERVER_STARTED'].format(port))
    app.run(port=port, host='0.0.0.0')
    logger.warning(LOG_TEMPLATES['SERVER_STOPPED'])
