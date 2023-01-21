import logging
import os
import sys

from templates_handler import get_template

try:
    os.mkdir('./logs')
except FileExistsError:
    pass

LOG_FORMATTER = get_template('log_templates')['log_formatter']
LOG_FILE = get_template('constants')['files']['log_file']


class Logger(logging.getLoggerClass()):
    def __init__(self, name):
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
