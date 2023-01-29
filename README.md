<a href="https://codeclimate.com/github/iwatkot/stravagrambot/maintainability"><img src="https://api.codeclimate.com/v1/badges/f332b498552ba5752255/maintainability" /></a>

# In development now

## How and why
This telegram bot is built on `aiogram` library and uses **Strava API** to help athletes get data from their Strava accounts via Telegram bot.<br>
Bot uses PostgreSQL to store data, which was accuqired from Flask webserver through the OAuth process.

## Strava OAuth
The bot generates OAuth links and send them to the user in Telegram. After user granted access to the bot, he will be redirected to the website, where bot's webserver is working. The webserver is built on `Flask` and designed for recieving OAuth redirects and to talk with Strava webhook service. Whenever the server recieves correct OAuth request, it launches oauth_init() to start the token exchange procedure and write data to the database.

## Logging
The bot uses custom `Logger` class based on Python's logging library. The custom class is pretty simple and designed for logging to the file and stdout in simple format with, where's the most of modules using the `__name__` variable for Logger name, which makes it easier to read the logs and finding errors. In addition to that, the admin user can use the /logs command to eqsily aquire the logs right from Telegram. The bot will send main log file to the admin user.

## Database
The bot uses PostgreSQL database for user's data. It stores user's telegram id, strava id and information about tokens. The `Database` class is designed for handling all DB operations: initial add, extract, check if the tokens is still active and updating tokens on refresh. Whenever the OAuth process is initiated the data about user in database will be completely deleted and then the new data will be add to the database. This solutuon is implemented to avoid possible conflicts when Telegram user will try to use diffrerent Strava accounts.

## Token refreshing
Whenever the bot is calling to Strava API for token exchange procedure, the API returns epoch time when access token will expire. The bot stores this time in databas and checks it when the user is trying to access the API. If token expire date is passed (or it will in the next 60 minutes), the bot will call Strava API to refresh the access token with refresh token. Then it will update the access token in database and request specified data from API with a new access token.

## Strava webhooks
The `WebHook` class is designed to handle Strava webhook subscription. It's also can be accessed with /webhook<> admin commands in Telegram with. Flask web server handles Strava webhook POST requests in webhook_challenge() and webhook_catcher() functions. The first function is designed to process webhook authentification with verify_token value. The second function isn't finished yet, it design to catch user updates.

## GPX creator
Very strange, but Strava API doesn't provide any option to download the GPX file for the activity, so the bot generates it by itself using data streams. The code, which handles GPX generating is literally copy-pasted from [PhysicsDan's GPXfromStravaAPI](https://github.com/PhysicsDan/GPXfromStravaAPI).

## Modules
_in development_
**api** -<br>
**bot** -<br>
**database_handler** -<br>
**flask_server** -<br>
**format_handler** -<br>
**log_handler** -<br>
**token_handler** -<br>
**webhook_handler** -<br>

## Commands
_List of inital commands, which shown in the main menu of the bot:_<br>
**/start** - Starts the bot and sends user short tips.<br>
**/auth** - Sends user Strava OAuth link to perform authentication process.<br>
**/stats<>** - Sends the user formatted stats from the Strava account. all - for overall stats and year for a current year stats.<br>
**/recent** - Sends the user formatted list of activities in the last 60 days with links to view a full information about specified activity.<br>
**/find** - Starts the state to find activities in the specified period of time (look state commands).<br>
**/weekavg** - Mostly the same as /statsyear, but the stats will be divided by the number of the current week so user can see his effort per week.<br><br>
_List of context commands, which not shown in the menu, but available at any moment:_<br>
**/activity<>** - Shows detailed information about activity, requires activity ID in the command.<br>
**/segment<>** - Shows detailed information about segment, requires segment ID in the command.<br>
**/download<>** - Generates GPX file from activity and sends it back to the user, requires activity ID in the command.<br><br>
_List of state commands, which not shown in the menu and available only in specific bot state:_<br>
**/cancel** - Cancels the current state (operation).<br>

## Admin commands
The bot will answer to admin commands only if user's Telegram ID is equal to `ADMIN` (from external file).<br>
**/logs** - Sends current log file back.<br>
**/users** - Sends back the complete users list with links to Strava accounts.<br>
**/webhook<>** - The commands to handle Strava webhook subscription. view - to check current subscription, delete - to delete (if active), subscribe - to create a new subscription.<br>

## To-Do
- Add content to `about` webpages.<br>
- User notifications from webhooks.<br>
- Commands for accessing athlete's gear<br>
- Commands for accessing athlete's routes<br>

## Changelog
**2023/01/29** - Added /starredsegments, whuch returns the list of athlete's starred segments.<br>
**2023/01/29** - Complete refactoring of format_handler.py. Partial refactoring of bot.py.<br>
**2023/01/27** - Added segements to the activity, added /segment command to check the segments. Added logger to the format_handler.<br>
**2023/01/26** - Fixed bug when /stats won't show info at all (or shows icorrect data).<br>
**2023/01/26** - Added `ru` locale for /find and /recent commands. Added locale to the webpages. Added admin commands for the webhook actions (subscribe, view, delete).<br>
**2023/01/25** - Added `ru` locale for /activity data.<br>
**2023/01/25** - Added HR and elevation data to the activities.<br>
**2023/01/25** - Added dialog for incorrect /find inputs. Now the bot will wait for correct data till user will input it or use the /cancel command.<br>
**2023/01/25** - Added `ru` locale for /stats commands, added /weekavg command with average stats per week in the current year.<br>
**2023/01/25** - Added simple pages for Flask webserver.<br>
**2023/01/24** - Added admin commands (/users and /logs) for easy access to logs and database via Telegram.<br>
**2023/01/24** - Removed `run.py`, integrated commands to the main bot file.