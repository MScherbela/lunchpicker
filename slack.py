import requests
import json
import os

def loadMessage():
    print(os.getcwd())
    with open('slackmessage.json') as f:
        data = json.load(f)
    return data

def sendLunchOptionsMessage(token):
    data = loadMessage()
    url = 'https://slack.com/api/chat.postMessage'
    # channel='TTCK4LQ7R/G01KRNNN44T' # workflow-test
    # channel='TTCK4LQ7R/D01BD5ESLTZ' # Michael Scherbela
    channel='U01BM5PTL3G'# Michael Scherbela user id

    r = requests.post(url, data=dict(token=token, channel=channel, blocks=json.dumps(data['blocks'])))
    return r
