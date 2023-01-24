# In developing now

## How and why
This telegram bot is built on `aiogram` library and uses **Strava API** to help athletes get data from their Strava accounts via Telegram bot.<br>
The bot has two locales: by default it's using **en**, but it the lang_code in message has **ru** code, the bot will use this language.

## Strava OAuth
The bot generates OAuth links and send them to the user in Telegram. After user granted access to the bot, he will be redirected to the website, where bot's webserver is working. The webserver is built on `Flask` and designed for recieving OAuth redirects and to talk with Strava webhook service.

## Logging
The bot uses custom `Logger` class based on Python's logging library. The custom class is pretty simple and designed for logging to the file and stdout in simple format with, where's the most of modules using the `__name__` variable for Logger name, which makes it easier to read the logs and finding errors.

## Database
The bot uses PostgreSQL database for user's data. It stores user's telegram id, strava id and information about tokens. The `Database` class is designed for handling all DB operations: initial add, extract, check if the tokens is still active and updating tokens on refresh.

## Token refreshing
_later_

## Strava webhooks
_later_

## Modules
_later_

## To-Do
_later_

## Changelog
_after beta release_