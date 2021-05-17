import requests
import json
from instance.config import SLACK_BOT_TOKEN

# url = 'https://slack.com/api/chat.postEphemeral'
url = 'https://slack.com/api/chat.postMessage'
# channel='TTCK4LQ7R/G01KRNNN44T' # workflow-test
# channel='TTCK4LQ7R/D01BD5ESLTZ' # Michael Scherbela
# channel='U01BM5PTL3G'
lunch_channel = 'C0170NJBXS5'
user_michael = 'U01BM5PTL3G'

with open('slack_templates/lunch_no_order_confirmation.json') as f:
    data = json.load(f)

data['blocks'][0]['text']['text'] = "Hi <@U01BM5PTL3G>,\n hope everything good?"
r = requests.post(url, data=dict(token=SLACK_BOT_TOKEN, channel=user_michael, blocks=json.dumps(data['blocks']), text="Hi <@U01BM5PTL3G>", link_names=True))
print(r)
print(r.status_code)
print(r.text)




