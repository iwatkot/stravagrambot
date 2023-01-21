import json


def get_template(file):
    filepath = 'templates/{}.json'.format(file)
    return json.load(open(filepath))
