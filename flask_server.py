import json
import logging

from flask import Flask, request, render_template
from flask_bootstrap import Bootstrap4
from decouple import config

from format_handler import get_template, get_content
from database_handler import DatabaseSession
from log_handler import Logger, LogTemplates
from token_handler import Token
from templates_handler import Constants

FLASK_TEMPLATES = get_template("flask_templates")
logger = Logger("flask_server")
flask_log = logging.getLogger("werkzeug")
flask_log.disabled = True

app = Flask(__name__)
bootstrap = Bootstrap4(app)


@app.route("/webhooks/", methods=["GET"])
def webhook_challenge():
    # logger.debug(LogTemplates[__name__].GET_REQUEST.format(request.full_path))
    verify_token = request.args.get("hub.verify_token")
    if verify_token == config("VERIFY_TOKEN"):
        hub_challenge = request.args.get("hub.challenge")
        # logger.debug(LogTemplates[__name__].RETURNING_HUB_CHALLENGE.format(
        #    hub_challenge))
        return json.dumps({"hub.challenge": hub_challenge}), 200


@app.route("/webhooks/", methods=["POST"])
def webhook_catcher():
    if request.content_type == "application/json":
        pass
        # json_data = request.json
        # logger.info(LogTemplates[__name__].WEBHOOK_RECIEVED.format(json_data))
    return "", 200


@app.route("/stravagramoauth")
def oauth():
    lang = locale_check(request)
    context = FLASK_TEMPLATES["locale"][lang]
    logger.debug(LogTemplates[__name__].GET_REQUEST.format(request.full_path))
    telegram_id = request.args.get("telegram_id")
    code = request.args.get("code")
    scope = request.args.get("scope")
    if "activity:read_all" not in scope:
        logger.debug(LogTemplates[__name__].BAD_REQUEST.format(telegram_id))
        message = FLASK_TEMPLATES["locale"][lang]["oauth_bad_message"]
        result = FLASK_TEMPLATES["locale"][lang]["oauth_bad"]
        return render_template(
            "pages/oauth.html", context=context, result=result, message=message
        )
    else:
        logger.debug(LogTemplates[__name__].GOOD_REQUEST.format(telegram_id, code))
        oauth_init(telegram_id, code)
        message = FLASK_TEMPLATES["locale"][lang]["oauth_good_message"]
        result = FLASK_TEMPLATES["locale"][lang]["oauth_good"]
        return render_template(
            "pages/oauth.html", context=context, result=result, message=message
        ), {"Refresh": "5; url=/"}


@app.route("/")
def index_page():
    lang = locale_check(request)
    context = FLASK_TEMPLATES["locale"][lang]
    return render_template("pages/index.html", context=context)


@app.route("/about")
@app.route("/changelog")
def pages():
    lang = locale_check(request)
    context = FLASK_TEMPLATES["locale"][lang]
    content = get_content(request.path, lang)
    return render_template(
        "pages{}.html".format(request.path), context=context, content=content
    )


def locale_check(request) -> str:
    """Returns the language code of GET request."""
    lang = (
        "ru"
        if request.accept_languages.best_match(Constants.SUPPORTED_LANGUAGES.value)
        == "ru"
        else "en"
    )
    return lang


def oauth_init(telegram_id: int, code: str) -> None:
    """Initiates token exchange procedure with code recieved from
    OAuth GET request."""
    token = Token(telegram_id, code=code)
    auth_data = token.exchange()
    if auth_data:
        oauth_session = DatabaseSession(telegram_id)
        oauth_session.add_user(auth_data)
        oauth_session.disconnect()
    else:
        logger.error(LogTemplates[__name__].OAUTH_FAILED)


def run_server():
    port = 80
    logger.info(LogTemplates[__name__].SERVER_STARTED.format(port))
    app.run(port=port, host="0.0.0.0")
    logger.warning(LogTemplates[__name__].SERVER_STOPPED)


if __name__ == "__main__":
    run_server()
