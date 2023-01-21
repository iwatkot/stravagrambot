import requests

from decouple import config


class WebHook:
    def __init__(self):
        self.client_id = config('CLIENT_ID')
        self.client_secret = config('CLIENT_SECRET')
        self.callback_url = config('CALLBACK_URL')
        self.verify_token = config('VERIFY_TOKEN')
        self.api_url = config('API_URL')
        self.params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        self.subcription_id = None

    def subscribe(self):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'callback_url': self.callback_url,
            'verify_token': self.verify_token,
        }
        response = requests.post(self.api_url, data=data).json()
        print(response)
        self.subcription_id = response['id']
        print(self.subcription_id)
        # logging subscription_id

    def view(self):
        response = requests.get(self.api_url, params=self.params).json()
        self.subcription_id = response[0]['id']
        print(self.subcription_id)
        # logging subcsription_id

    def delete(self):
        response = requests.delete(self.api_url + '/{}'.format(
            self.subcription_id), params=self.params).status_code
        if response == 204:
            pass
            # logging subsc deleted
        

    


webhook = WebHook()
#webhook.subscribe()
webhook.view()
#webhook.delete()


data = {
    "aspect_type": "update",
    "event_time": 1516126040,
    "object_id": 1360128428,
    "object_type": "activity",
    "owner_id": 134815,
    "subscription_id": 120475,
    "updates": {
        "title": "Messy"
    }
}
headers = {'Content-Type': 'application/json'}
response = requests.post('http://stravagram.space/webhooks/', headers=headers, data=data)
print(response)


#data = {
#    'client_id': config('CLIENT_ID'),
#    'client_secret': config('CLIENT_SECRET'),
#    'callback_url': config('CALLBACK_URL'),
#    'verify_token': config('VERIFY_TOKEN')
#}

#response = requests.post('https://www.strava.com/api/v3/push_subscriptions', data=data).json()
#print(response)