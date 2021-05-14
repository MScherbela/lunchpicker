import requests
import json
from instance.config import SLACK_BOT_TOKEN

url = 'https://slack.com/api/chat.postEphemeral'
# channel='TTCK4LQ7R/G01KRNNN44T' # workflow-test
# channel='TTCK4LQ7R/D01BD5ESLTZ' # Michael Scherbela
# channel='U01BM5PTL3G'
lunch_channel = 'C0170NJBXS5'
user_michael = 'U01BM5PTL3G'

with open('slack_templates/lunch_no_order_confirmation.json') as f:
    data = json.load(f)

#
r = requests.post(url, data=dict(token=SLACK_BOT_TOKEN, channel=lunch_channel, blocks=json.dumps(data['blocks']), user=user_michael))
print(r)
print(r.status_code)
print(r.text)




