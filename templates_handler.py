import os
import json

absolute_path = os.path.dirname(__file__)


def get_template(file):
    filepath = os.path.join(absolute_path, 'templates/{}.json'.format(file))
    return json.load(open(filepath))
