import requests
import json
import os
import copy

with open('slackmessage.json') as f:
    MESSAGE_TEMPLATE = json.load(f)

def loadMessage():
    print(os.getcwd())
    with open('slackmessage.json') as f:
        data = json.load(f)
    return data

def sendLunchOptionsMessage(token):
    restaurant = 'Fladerei'
    options = ['Tagesfladen', 'Schinken Champignon', 'Sauerrahm Speck Zwiebel']
    name = 'Michael'
    user_id = 'U01BM5PTL3G'
    msg = buildLunchMessage(name, user_id, restaurant, options)

    url = 'https://slack.com/api/chat.postMessage'
    # channel='TTCK4LQ7R/G01KRNNN44T' # workflow-test
    # channel='TTCK4LQ7R/D01BD5ESLTZ' # Michael Scherbela
    channel='U01BM5PTL3G'# Michael Scherbela user id

    r = requests.post(url, data=dict(token=token, channel=channel, blocks=json.dumps(msg['blocks'])))
    return r

def buildLunchMessage(name, user_id, restaurant, options):
    msg = copy.deepcopy(MESSAGE_TEMPLATE)
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('RESTAURANT_PLACEHOLDER', restaurant).replace('NAME_PLACEHOLDER', name)

    option_objects = [dict(text=dict(type='plain_text', text=o), value=str(i)) for i,o in enumerate(options)]
    msg['blocks'][1]['accessory']['options'] = option_objects
    msg['blocks'][1]['accessory']['initial_option'] = option_objects[0]

    msg['blocks'][3]['elements'][2]['url'] = f'https://lunchbot.scherbela.com/addDish/{user_id}'
    return msg

if __name__ == '__main__':
    pass





