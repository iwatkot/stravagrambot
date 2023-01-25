# In developing now

## How and why
This telegram bot is built on `aiogram` library and uses **Strava API** to help athletes get data from their Strava accounts via Telegram bot.<br>
Bot uses PostgreSQL to store data, which was accuqired from Flask webserver through the OAuth process.

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

## GPX creator
_later_

## Modules
_later_

## Commands
_later_

## Admin commands

## To-Do
- Dialog awaiting for incorrect inputs in /find command<br>
- Commands for accessing segments on Strava.<br>
- Commands for accessing athlete's gear<br>
- Commands for accessing athlete's routes<br>


## Changelog
**2023/01/25** - Added simple pages for Flask webserver.<br>
**2023/01/24** - Added admin commands (/users and /logs) for easy access to logs and database via Telegram.<br>
**2023/01/24** - Removed `run.py`, integrated commands to the main bot file.