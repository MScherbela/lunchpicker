import requests
import json
import os
import copy
import logging
from instance.config import LUNCH_CHANNEL

logger = logging.getLogger()

with open('slack_lock.txt') as f:
    if 'lock' in f.read().lower():
        SLACK_LOCKED = True
    else:
        SLACK_LOCKED = False

MESSAGE_TEMPLATES = {}
for fname in os.listdir('slack_templates'):
    if fname.endswith('.json'):
        key = fname[:-5]
        with open(f'slack_templates/{fname}') as f:
            MESSAGE_TEMPLATES[key] = json.load(f)

def loadMessage():
    print(os.getcwd())
    with open('slackmessage.json') as f:
        data = json.load(f)
    return data

def sendMessageToChannel(channel, msg, token, text=None, ephemeral_user=None):
    """
    Posts a message to a slack channel.

    Args:
        channel (str): Channel id or user id for direct messages
        msg: Message object, containin a blocks field
        token (str): Secret auth token
        text (str): Fallback string to show when message cannot be rendered (e.g. mobile preview)
        ephemeral_user (str or None): If None, message is sent publicly to channel. If a user-id is specified, an ephemeral message visiable only to this user will be posted in the channel.

    Returns:
        JSON response
    """
    if SLACK_LOCKED and channel not in ('U01BM5PTL3G', 'G01KRNNN44T'):
        logger.warning(f"Sending of slack messages has been disabled, but the bot tried to send a message to channel {channel}")
        return None

    data = dict(token=token, channel=channel, blocks=json.dumps(msg['blocks']), link_names=True)
    if ephemeral_user is None:
        url = 'https://slack.com/api/chat.postMessage'
    else:
        url = 'https://slack.com/api/chat.postEphemeral'
        data['user'] = ephemeral_user
    if text is not None:
        data['text'] = text
    logger.debug(f"Slack request: {url}, {data}")
    r = requests.post(url, data=data)
    logger.debug(r.json())
    return r

def sendMessageToUser(user, msg, token, text=None):
    if not user.active:
        logger.warning(f"Tried to send message to inactive user: {user.get_full_name()}. Message has NOT been sent")
        return None
    return sendMessageToChannel(user.slack_id, msg, token, text)

def sendLunchOptionsMessage(user, restaurant, possible_dishes, proposed_dish, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['lunch_options'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('RESTAURANT_PLACEHOLDER', restaurant.name).replace('NAME_PLACEHOLDER', user.first_name)
    msg['blocks'][1]['accessory']['options'] = [dict(text=dict(type='plain_text', text=f"{d.name} (€ {d.price / 100:.2f})"), value=str(d.id)) for d in possible_dishes]
    proposed_option = [d for d in msg['blocks'][1]['accessory']['options'] if d['value'] == str(proposed_dish.id)]
    msg['blocks'][1]['accessory']['initial_option'] = proposed_option[0]
    msg['blocks'][3]['elements'][2]['url'] = f'https://lunchbot.scherbela.com/profile/{user.id}'
    if restaurant.name == 'Pasta Day':
        msg['blocks'][3]['elements'] = msg['blocks'][3]['elements'][:2] # remove something-else-button for Pasta day
    fallback_text = f"Hi {user.first_name}, we're getting lunch from {restaurant.name}. What do you want?"
    return sendMessageToUser(user, msg, token, fallback_text)


def sendRestaurantOptionsMessage(restaurants, leading_restaurant, channel_name, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['restaurant_options'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('RESTAURANT_PLACEHOLDER', leading_restaurant.name)
    msg['blocks'][1]['elements'][0]['options'] = [dict(text=dict(type='plain_text', text=r.name), value=str(r.id)) for r in restaurants]
    msg['blocks'][1]['elements'][0]['initial_option'] = dict(text=dict(type='plain_text', text=leading_restaurant.name), value=str(leading_restaurant.id))
    if channel_name == 'lunch':
        channel = 'C0170NJBXS5'
    elif channel_name == 'test':
        channel = 'G01KRNNN44T'
    elif channel_name == 'michael':
        channel = 'U01BM5PTL3G'
    else:
        logger.error(f"Invalid channel name for sendRestaurantOptions: {channel_name}")
        raise ValueError("Invalid channel name")

    return sendMessageToChannel(channel, msg, token, f"How about lunch from {leading_restaurant.name}?")


def sendVoteConfirmation(user, vote_type, restaurant_name, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['vote_confirmation'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('VOTETYPE_PLACEHOLDER', vote_type).replace('RESTAURANT_PLACEHOLDER', restaurant_name)
    return sendMessageToChannel(LUNCH_CHANNEL, msg, token, text="Vote registered.", ephemeral_user=user.slack_id)


def sendLunchConfirmation(user, dish_name, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['lunch_confirmation'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('DISH_PLACEHOLDER', dish_name)
    return sendMessageToUser(user, msg, token, text="Order confirmed!")


def sendLunchNoOrderConfirmation(user, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['lunch_no_order_confirmation'])
    return sendMessageToChannel(LUNCH_CHANNEL, msg, token, text="Ok, I'll not order for you.", ephemeral_user=user.slack_id)


def sendTooLateMessage(user, orderer, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['too_late'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('ORDERER_NAME', orderer.get_full_name())
    return sendMessageToUser(user, msg, token, text=f"You might be too late. Check with {orderer.get_full_name()}.")


def sendSubscribeMessage(user, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['subscribe_message'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('NAME_PLACEHOLDER', user.first_name)
    return sendMessageToUser(user, msg, token, text=f"Welcome to the lunchbot!")


def sendUnsubscribeMessage(user, token):
    msg = copy.deepcopy(MESSAGE_TEMPLATES['unsubscribe_message'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('NAME_PLACEHOLDER', user.first_name)
    return sendMessageToUser(user, msg, token, text=f"You've been unsubscribed from the lunchbot.")


def sendOrderSummary(user, order_list, restaurant_name, token):
    """order_list ist a list of tuples, containing (dish_name, user_name)"""
    msg = copy.deepcopy(MESSAGE_TEMPLATES['order_summary'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace('NAME_PLACEHOLDER', f"@{user.slack_id}")
    msg['blocks'][3]['text']['text'] = msg['blocks'][3]['text']['text'].replace('RESTAURANT_PLACEHOLDER', restaurant_name)

    orders = [dict(value=str(i), text=dict(type="mrkdwn", text=f"*{o[0]}* ({o[2]}, EUR {o[1]/100:.2f})")) for i,o in enumerate(order_list)]
    msg['blocks'][3]['accessory']['options'] = orders
    return sendMessageToChannel(LUNCH_CHANNEL, msg, token, text=f"Hi <@{user.slack_id}>, please take care of today's order!")

def sendOrderSummaryPasta(user, users_joining, grams_of_pasta, token):
    """order_list ist a list of tuples, containing (dish_name, user_name)"""
    n_people = len(users_joining)
    usernames = ", ".join([u.first_name for u in users_joining])

    msg = copy.deepcopy(MESSAGE_TEMPLATES['order_summary_pasta'])
    msg['blocks'][0]['text']['text'] = msg['blocks'][0]['text']['text'].replace(
        'NAME_PLACEHOLDER', user.first_name).replace(
        'N_PEOPLE_PLACEHOLDER', str(n_people)).replace(
        'USERNAMES_PLACEHOLDER', usernames)

    msg['blocks'][2]['text']['text'] = msg['blocks'][2]['text']['text'].replace(
        'N_PEOPLE_PLACEHOLDER', str(n_people)).replace(
        'GRAM_PASTA_PLACEHOLDER', str(grams_of_pasta))

    return sendMessageToUser(user, msg, token, text=f"Hi {user.first_name}, please take care of cooking pasta today!")


def getUserId(payload):
    return payload['user']['id']


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





