from subprocess import Popen

from bot import run_bot

if __name__ == '__main__':
    Popen(['python', 'flask_server.py'])
    run_bot()
