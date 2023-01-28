import json
import logging

from flask import Flask, request, render_template
from flask_bootstrap import Bootstrap4
from decouple import config

from format_handler import get_template, get_content
from database_handler import DataBase
from log_handler import Logger
from token_handler import Token

FLASK_TEMPLATES = get_template('flask_templates')
LOG_TEMPLATES = get_template('log_templates')['flask_server']
SUPPORTED_LANGUAGES = ["en", "ru"]
logger = Logger('flask_server')
flask_log = logging.getLogger('werkzeug')
flask_log.disabled = True

app = Flask(__name__)
bootstrap = Bootstrap4(app)


@app.route(FLASK_TEMPLATES['oauth']['webhooks_marker'], methods=["GET"])
def webhook_challenge():
    logger.debug(LOG_TEMPLATES['GET_REQUEST'].format(request.full_path))
    verify_token = request.args.get('hub.verify_token')
    if verify_token == config('VERIFY_TOKEN'):
        hub_challenge = request.args.get('hub.challenge')
        logger.debug(LOG_TEMPLATES['RETURNING_HUB_CHALLENGE'].format(
            hub_challenge))
        return json.dumps({'hub.challenge': hub_challenge}), 200


@app.route(FLASK_TEMPLATES['oauth']['webhooks_marker'], methods=["POST"])
def webhook_catcher():
    if request.content_type == 'application/json':
        json_data = request.json
        logger.info(LOG_TEMPLATES['WEBHOOK_RECIEVED'].format(json_data))
    return '', 200


@app.route(FLASK_TEMPLATES['oauth']['oauth_marker'])
def oauth():
    lang = 'ru' if request.accept_languages.best_match(
        SUPPORTED_LANGUAGES) == 'ru' else 'en'
    context = FLASK_TEMPLATES['locale'][lang]
    logger.debug(LOG_TEMPLATES['GET_REQUEST'].format(request.full_path))
    telegram_id = request.args.get('telegram_id')
    code = request.args.get('code')
    scope = request.args.get('scope')
    if 'activity:read_all' not in scope:
        logger.debug(LOG_TEMPLATES['BAD_REQUEST'].format(telegram_id))
        message = FLASK_TEMPLATES['locale'][lang]['oauth_bad_message']
        result = FLASK_TEMPLATES['locale'][lang]['oauth_bad']
        return render_template('pages/oauth.html', context=context,
                               result=result, message=message)
    else:
        logger.debug(LOG_TEMPLATES['GOOD_REQUEST'].format(
                    telegram_id, code))
        oauth_init(telegram_id, code)
        message = FLASK_TEMPLATES['locale'][lang]['oauth_good_message']
        result = FLASK_TEMPLATES['locale'][lang]['oauth_good']
        return render_template('pages/oauth.html', context=context,
                               result=result, message=message), {
                               "Refresh": "5; url=/"}


@app.route('/')
def index_page():
    lang = locale_check(request)
    context = FLASK_TEMPLATES['locale'][lang]
    return render_template('pages/index.html', context=context)


@app.route('/about')
@app.route('/changelog')
def pages():
    lang = locale_check(request)
    context = FLASK_TEMPLATES['locale'][lang]
    content = get_content(request.path, lang)
    return render_template(
        'pages{}.html'.format(request.path),
        context=context, content=content)


def locale_check(request):
    lang = 'ru' if request.accept_languages.best_match(
        SUPPORTED_LANGUAGES) == 'ru' else 'en'
    return lang


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


def run_server():
    port = 80
    logger.info(LOG_TEMPLATES['SERVER_STARTED'].format(port))
    app.run(port=port, host='0.0.0.0')
    logger.warning(LOG_TEMPLATES['SERVER_STOPPED'])


if __name__ == '__main__':
    run_server()
