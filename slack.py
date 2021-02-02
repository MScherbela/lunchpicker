import requests
import json
import os
import copy

with open('slack_templates/lunch_options.json') as f:
    LUNCH_OPTIONS_TEMPLATE = json.load(f)

with open('slack_templates/lunch_confirmation.json') as f:
    LUNCH_CONFIRMATION_TEMPLATE = json.load(f)

with open('slack_templates/lunch_no_order_confirmation.json') as f:
    LUNCH_NO_ORDER_CONFIRMATION_TEMPLATE = json.load(f)

with open('slack_templates/order_summary.json') as f:
    LUNCH_ORDER_SUMMARY_TEMPLATE = json.load(f)

def loadMessage():
    print(os.getcwd())
    with open('slackmessage.json') as f:
        data = json.load(f)
    return data

def sendMessage(channel, msg, token, text=None):
    url = 'https://slack.com/api/chat.postMessage'
    data = dict(token=token, channel=channel, blocks=json.dumps(msg['blocks']))
    if text is not None:
        data['text'] = text
    if channel == 'U01BM5PTL3G':
        r = requests.post(url, data=data)
    else:
        raise ValueError("Warning: Sending of messages disabled")
    # r = requests.post(url, data=data)
    return r

def sendLunchOptionsMessage(user, restaurant, possible_dishes, proposed_dish, token):
    msg = copy.deepcopy(LUNCH_OPTIONS_TEMPLATE)
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('RESTAURANT_PLACEHOLDER', restaurant.name).replace('NAME_PLACEHOLDER', user.first_name)
    msg['blocks'][1]['accessory']['options'] = [dict(text=dict(type='plain_text', text=d.name), value=str(d.id)) for d in possible_dishes]
    msg['blocks'][1]['accessory']['initial_option'] = dict(text=dict(type='plain_text', text=proposed_dish.name), value=str(proposed_dish.id))
    msg['blocks'][3]['elements'][2]['url'] = f'https://lunchbot.scherbela.com/profile/{user.id}'
    fallback_text = f"Hi {user.first_name}, we're getting lunch from {restaurant.name}. What do you want?"
    return sendMessage(user.slack_id, msg, token, fallback_text)

def sendLunchConfirmation(user, dish_name, token):
    msg = copy.deepcopy(LUNCH_CONFIRMATION_TEMPLATE)
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('DISH_PLACEHOLDER', dish_name)
    return sendMessage(user.slack_id, msg, token, text="Order confirmed!")

def sendLunchNoOrderConfirmation(user, token):
    msg = copy.deepcopy(LUNCH_NO_ORDER_CONFIRMATION_TEMPLATE)
    return sendMessage(user.slack_id, msg, token, text="Ok, I'll not order for you.")

def sendOrderSummary(user, order_list, restaurant_name, token):
    """order_list ist a list of tuples, containing (dish_name, user_name)"""
    msg = copy.deepcopy(LUNCH_ORDER_SUMMARY_TEMPLATE)
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('NAME_PLACEHOLDER', user.first_name)
    msg['blocks'][3]['text']['text'] = msg['blocks'][3]['text']['text'].replace('RESTAURANT_PLACEHOLDER', restaurant_name)

    orders = [dict(text=dict(type="mrkdwn", text=f"*{o[0]}* ({o[1]})")) for o in order_list]
    msg['blocks'][3]['accessory']['options'] = orders
    return sendMessage(user.slack_id, msg, token, text=f"Hi {user.first_name}, please take care of today's order!")

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





