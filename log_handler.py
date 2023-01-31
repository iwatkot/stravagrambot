import logging
import os
import sys

absolute_path = os.path.dirname(__file__)

os.makedirs(os.path.join(absolute_path, 'logs'), exist_ok=True)

LOG_FORMATTER = "%(name)s | %(asctime)s | %(levelname)s | %(message)s"
LOG_FILE = os.path.join(absolute_path, 'logs/main_log.txt')


class Logger(logging.getLoggerClass()):
    """Handles logging to the file and stroudt with timestamps."""
    def __init__(self, name: str):
        super().__init__(name)
        self.setLevel(logging.DEBUG)
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.file_handler = logging.FileHandler(
            filename=LOG_FILE, mode='a')
        self.fmt = LOG_FORMATTER
        self.stdout_handler.setFormatter(logging.Formatter(LOG_FORMATTER))
        self.file_handler.setFormatter(logging.Formatter(LOG_FORMATTER))
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)


def get_log_file() -> str:
    """Returns the path to the main_log file."""
    return LOG_FILE
