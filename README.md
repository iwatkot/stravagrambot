<a href="https://codeclimate.com/github/iwatkot/stravagrambot/maintainability"><img src="https://api.codeclimate.com/v1/badges/f332b498552ba5752255/maintainability" /></a>

# In development now

## How and why
This telegram bot is built on `aiogram` library and uses **Strava API** to help athletes get data from their Strava accounts via Telegram bot.<br>
The bot uses `PostgreSQL` to store data and operates with it through the `SQLAlchemy`. The access data in the database acquiring from the Flask web server through the OAuth process.

## Strava OAuth
The bot generates OAuth links and sends them to the user in Telegram. After the user is granted access to the bot, he will be redirected to the website, where the bot's webserver is working. The webserver is built on `Flask` and designed for receiving OAuth redirects and talking with Strava webhook service. Whenever the server receives the correct OAuth request, it launches oauth_init() to start the token exchange procedure and write data to the database.

## Logging
The bot uses a custom `Logger` class based on Python's logging library. The custom class is pretty simple and designed for logging to the file and stdout in a simple format, where most of the modules use the `__name__` variable for the Logger name, which makes it easier to read the logs and find errors. In addition to that, the admin user can use the /logs command to easily acquire the logs right from Telegram. The bot will send the main log file to the admin user.

## Database
The bot uses the PostgreSQL database for the user's data. It stores the user's telegram id, Strava id and information about tokens. The `Database` class is designed for handling all DB operations: initial add, extract, check if the tokens are still active and updating tokens on refresh. Whenever the OAuth process is initiated the data about the user in the database will be completely deleted and then new data will be added to the database. This solution is implemented to avoid possible conflicts when Telegram user will try to use different Strava accounts.

## Token refreshing
Whenever the bot is calling to Strava API for the token exchange procedure, the API returns the epoch time when the access token will expire. The bot stores this time in databases and checks it when the user is trying to access the API. If the token expiration date is passed (or it will in the next 60 minutes), the bot will call Strava API to refresh the access token with the refresh token. Then it will update the access token in the database and request specified data from API with a new access token.

## Strava webhooks
The `WebHook` class is designed to handle Strava webhook subscriptions. It's also can be accessed with /webhook<> admin commands in Telegram. The Flask web server handles Strava webhook POST requests in webhook_challenge() and webhook_catcher() functions. The first function is designed to process webhook authentification with verify_token value. The second function isn't finished yet, it is designed to catch user updates.

## GPX creator
Very strange, but Strava API doesn't provide any option to download the GPX file for the activity, so the bot generates it by itself using data streams. The code, which handles GPX generating is copy-pasted from [PhysicsDan's GPXfromStravaAPI](https://github.com/PhysicsDan/GPXfromStravaAPI).

## Modules
**analytics_handler** - contains classes for generating analytics based on activities (right now only one for year forecast).<br>
**api_handler** - handles data receiving from the API using information from database_handler and token_handler<br>
**bot** - the main script, which handles interaction with telegram user<br>
**database_handler** - handles operations with database, such as inserting data from the ouath_init() and getting access_tokens for API calls<br>
**flask_server** - handles OAuth and webhooks request. Also provides access to simple webpages with some info<br>
**format_handler** - handles the nastiest part of the bot: formatting raw data from the API to something that humans can understand. Since the raw data sometimes is a little bit weird, the module has a lot of functions to convert data.<br>
**image_handler** - contains a class, which is designed for creating images with activity data.<br>
**log_handler** - a short and simple module, which provides a Logger class all across the bot modules.<br>
**templates_handler** - stores some constants and templates to use in other modules.<br>
**token_handler** - handles API exchange tokens procedure: getting access token after init and refreshes the token, when it's expired.<br>
**webhook_handler** - handles Strava webhook subscription (subscribe, view, delete).<br>

## Menu buttons
_add later_


## Admin commands
The bot will answer admin commands only if the user's Telegram ID is equal to `ADMIN` (from an external file).<br>
**/logs** - Sends current log file back.<br>
**/users** - Send back the complete users list with links to Strava accounts.<br>
**/webhook<>** - The commands to handle the Strava webhook subscription. view - to check the current subscription, delete - to delete (if active), subscribe - to create a new subscription.<br>


## Changelog
**2023/03/12** - Added new menu for analytics. Added one feature for this menu: year forecast, which consists of three options (distance, time and elevation).<br>
**2023/03/12** - Added feature to create images for Instagram stories.<br>
**2023/03/02** - Fixed bug when no gear in activity caused format_handler to crash.<br> 
**2023/02/26** - Fixed bug when the bot used refresh token after getting new access token.<br>
**2023/02/26** - The bot uses a menu now to interact with the user.<br>
**2023/02/25** - Moved from /commands to inline buttons.<br>
**2023/02/25** - Massive changes in the way templates are stored. Moved to SQLAlchemy from raw SQL requests.<br>
**2023/01/31** - Massive refactoring of most modules.<br>
**2023/01/30** - Added average speed and pace for all stats commands.<br>
**2023/01/29** - Added /starredsegments, which returns the list of athlete's starred segments.<br>
**2023/01/29** - Complete refactoring of format_handler.py. Partial refactoring of bot.py.<br>
**2023/01/27** - Added segments to the activity, and added /segment command to check the segments. Added logger to the format_handler.<br>
**2023/01/26** - Fixed bug when /stats won't show info at all (or shows incorrect data).<br>
**2023/01/26** - Added `ru` locale for /find and /recent commands. Added locale to the web pages. Added admin commands for the webhook actions (subscribe, view, delete).<br>
**2023/01/25** - Added `ru` locale for /activity data.<br>
**2023/01/25** - Added HR and elevation data to the activities.<br>
**2023/01/25** - Added dialog for incorrect /find inputs. Now the bot will wait for correct data till the user will input it or use the /cancel command.<br>
**2023/01/25** - Added `ru` locale for /stats commands, added /weekavg command with average stats per week in the current year.<br>
**2023/01/25** - Added simple pages for the Flask web server.<br>
**2023/01/24** - Added admin commands (/users and /logs) for easy access to logs and database via Telegram.<br>
**2023/01/24** - Removed `run.py`, and integrated commands to the main bot file.