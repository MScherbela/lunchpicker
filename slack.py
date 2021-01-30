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

def sendLunchOptionsMessage(user, restaurant, possible_dishes, proposed_dish, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATE)
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('RESTAURANT_PLACEHOLDER', restaurant.name).replace('NAME_PLACEHOLDER', user.first_name)
    msg['blocks'][1]['accessory']['options'] = [dict(text=dict(type='plain_text', text=d.name), value=str(d.id)) for d in possible_dishes]
    msg['blocks'][1]['accessory']['initial_option'] = dict(text=dict(type='plain_text', text=proposed_dish.name), value=str(proposed_dish.id))
    msg['blocks'][3]['elements'][2]['url'] = f'https://lunchbot.scherbela.com/addDish/{user.slack_id}'
    with open('/data/message.json', 'w') as f:
       json.dump(msg, f, indent=4)

    url = 'https://slack.com/api/chat.postMessage'
    channel=user.slack_id
    r = requests.post(url, data=dict(token=token, channel=channel, blocks=json.dumps(msg['blocks'])))
    return r

def parseSlackRequestPayload(payload):
    user = getUserId(payload)
    button = getSlackRequestButtonValue(payload)
    if button is None:
        return dict(user=user, button='')
    if button == 'yes':
        dish_id = getSelectedDish(payload)
        return dict(user=user, button=button, dish_id=dish_id)
    else:
        return dict(user=user, button=button)

def getUserId(payload):
    return payload['user']['id']

def getSelectedDish(payload):
    return int(payload['state']['values']['selection_section']['static_select-action']['selected_option']["value"])

def getSlackRequestButtonValue(payload):
    if payload['type'] != "block_actions":
        return None
    if 'actions' not in payload:
        return None
    for a in payload['actions']:
        if a['type'] == 'button':
            return a['value']
    else:
        return None


if __name__ == '__main__':
    pass





