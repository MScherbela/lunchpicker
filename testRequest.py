import requests
import json

with open('slackmessage.json') as f:
    data = json.load(f)

# Send message using webhook
# url = 'https://hooks.slack.com/services/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'
# r = requests.post(url, json=data)
# print(r)
# print(r.status_code)


url = 'https://slack.com/api/chat.postMessage'
bot_token=''
channel='TTCK4LQ7R/G01KRNNN44T' # workflow-test
# channel='TTCK4LQ7R/D01BD5ESLTZ' # Michael Scherbela
channel='U01BM5PTL3G'

r = requests.post(url, data=dict(token=bot_token, channel=channel, blocks=json.dumps(data['blocks'])))
print(r)
print(r.status_code)
print(r.text)

