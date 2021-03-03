import logging

try:
    logging.basicConfig(filename='/data/lunchbot.log', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
except FileNotFoundError:
    logging.basicConfig(filename='lunchbot.log', level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

import flask
import slack
import json
import datetime
import random
import sqlalchemy.sql.functions as sqlfunc
from extensions import *
from models import *

app = flask.Flask(__name__)
app.config.from_pyfile('config.py')
app.config.from_pyfile('instance/config.py')
SLACK_BOT_TOKEN = app.config['SLACK_BOT_TOKEN']

admin.init_app(app)
add_admin_views()
db.init_app(app)
basic_auth.init_app(app)
scheduler.init_app(app)
scheduler.start()


# %% Scheduler tasks
@scheduler.task('cron', id='cast_bot_vote', minute=30, hour=8, day_of_week="mon,tue,wed,thu,fri")
def castBotVoteTask():
    with app.app_context():
        castBotVoteForRestaurant(prevent_revote=False)
        sendRestaurantOptions('test')


@scheduler.task('cron', id='send_restaurant_options', minute=30, hour=9, day_of_week="mon,tue,wed,thu,fri")
def sendRestaurantOptionsTask():
    with app.app_context():
        castBotVoteForRestaurant(prevent_revote=True) # should already be decided; just in case
        sendRestaurantOptions()


@scheduler.task('cron', id='send_lunch_options', minute=45, hour=10, day_of_week='mon,tue,wed,thu,fri')
def sendLunchOptionsTask():
    with app.app_context():
        selectRestaurant()
        sendLunchProposalToAll()


@scheduler.task('cron', id='send_order_summary', minute=15, hour=11, day_of_week='mon,tue,wed,thu,fri')
def sendOrderSummaryTask():
    with app.app_context():
        sendOrderSummary()
        updateDishWeights()


# %% Getter Methods
def getUsersWithConfirmedOrder(date=None):
    if date is None:
        date = datetime.date.today()
    return db.session.query(User).filter(
        User.id == DishChoice.user_id).filter(
        DishChoice.date == date).filter(
        DishChoice.status == 1).all()


def getActiveUsers():
    return User.query.filter_by(active=True, is_bot=False).all()


def getActiveRestaurants():
    return Restaurant.query.filter_by(active=True).all()


def getTodaysRestaurant():
    today = datetime.date.today()
    restaurant_choice = RestaurantChoice.query.filter_by(date=today).first()
    if restaurant_choice is None:
        return None
    else:
        return restaurant_choice.restaurant


def getPossibleDishes(user, restaurant):
    return db.session.query(Dish).filter(
        Dish.id == UserDishWeight.dish_id).filter(
        UserDishWeight.user_id == user.id).filter(
        Dish.restaurant_id == restaurant.id).all()


def is_pasta_day(date):
    choice = RestaurantChoice.query.filter_by(date=date).first()
    if choice is None:
        return None
    else:
        return choice.restaurant.name == 'Pasta Day'

def get_pastabot():
    return User.query.filter_by(first_name='Pasta Bot').first()


# %% Setter Methods
def addUserIfNotExists(user_data):
    user = User.query.filter_by(slack_id=user_data['id']).first()
    if user is None:
        first, last = user_data['name'].split('.')
        user = User(first_name=first.title(), last_name=last.title(), slack_id=user_data['id'], active=True)
        db.session.add(user)
        db.session.commit()

        default_dishes = Dish.query.filter_by(default=True).all()
        for d in default_dishes:
            db.session.add(UserDishWeight(user_id=user.id, dish_id=d.id, weight=0.1))
    else:
        user.active = True
    db.session.commit()
    return user

def addDish(dish_name, dish_price, user, restaurant, confirm_choice):
    dish = Dish(name=dish_name, restaurant_id=restaurant.id, dish_price=dish_price)
    db.session.add(dish)
    db.session.commit()
    db.session.add(UserDishWeight(user_id=user.id, dish_id=dish.id))
    db.session.commit()
    if confirm_choice:
        setUserChoice(user.id, dish.id)


def updateDishWeights():
    """Calculate dish preferences based on order history"""
    for user in User.query.all():
        weights = UserDishWeight.query.filter_by(user_id=user.id).all()
        for w in weights:
            n_orders = DishChoice.query.filter_by(user_id=user.id, dish_id=w.dish_id, status=1).count()
            w.weight = n_orders + 0.1
    db.session.commit()


def setUserChoice(user_id, dish_id):
    today = datetime.date.today()
    DishChoice.query.filter_by(date=today, user_id=user_id).delete()
    db.session.add(DishChoice(date=today, user_id=user_id, dish_id=dish_id, status=2 if dish_id is None else 1))
    db.session.commit()


# %% Voting / Selecting logic
def calculate_karma(user_data):
    karma = 1.0 # Add base karma
    karma += user_data['contributions']
    karma += user_data['pasta_contributions'] # Pasta counts 2x (it's already included once in regular contributions)
    karma += user_data['meals_served'] * 0.2  # Give additional karma for serving large groups
    return 10.0 * karma / (1+user_data['orders']) + user_data['credit'] / 1000 # +1 karma for every 10 EUR (1000 cent)

def getAllUserKarma():
    all_users = User.query.filter_by(is_bot=False).all()

    user_data = {u.id:dict(id=u.id, orders=0, contributions=0, pasta_contributions=0, meals_served=0, credit=u.credit) for u in all_users}
    for user_id in user_data:
        user_data[user_id]['name'] = User.query.get(user_id).get_full_name()

    orders = db.session.query(User.id, sqlfunc.count(DishChoice.id)).filter(
        DishChoice.user_id == User.id,
        DishChoice.status == 1).group_by(User.id).all()
    for x in orders:
        user_data[x[0]]['orders'] = x[1]

    contributions = db.session.query(User.id, sqlfunc.count(OrdererChoice.id)).filter(
        OrdererChoice.user_id == User.id).group_by(User.id).all()
    for x in contributions:
        user_data[x[0]]['contributions'] = x[1]

    pasta_day_id = Restaurant.query.filter_by(name='Pasta Day').first().id
    pasta_contributions = db.session.query(User.id, sqlfunc.count(RestaurantChoice.id)).filter(
        User.id == OrdererChoice.user_id,
        OrdererChoice.date == RestaurantChoice.date,
        RestaurantChoice.restaurant_id == pasta_day_id).group_by(User.id).all()
    for x in pasta_contributions:
        user_data[x[0]]['pasta_contributions'] = x[1]

    meals_served = db.session.query(User.id, sqlfunc.count(DishChoice.id)).filter(
        User.id == OrdererChoice.user_id,
        OrdererChoice.date == DishChoice.date,
        DishChoice.status == 1).group_by(User.id).all()
    for x in meals_served:
        user_data[x[0]]['meals_served'] = x[1]

    user_data = [(calculate_karma(d)+1e-6*i, d) for i,d in enumerate(user_data.values())] # Add tiny amounts of karma to differentiate users with identical karma
    user_data = sorted(user_data, reverse=True)
    return user_data


def voteForRestaurant(restaurant_id, user_id, date=None, weight=None):
    if date is None:
        date = datetime.date.today()
    if weight is None:
        weight = 0.1 if user_id is None else 1.0

    RestaurantVote.query.filter_by(restaurant_id=restaurant_id, user_id=user_id, date=date).delete()
    db.session.add(RestaurantVote(restaurant_id=restaurant_id, user_id=user_id, date=date, weight=weight))
    db.session.commit()


def castBotVoteForRestaurant(date=None, prevent_revote=True):
    if date is None:
        date = datetime.date.today()
    existing_bot_vote = RestaurantVote.query.filter_by(date=date, user_id=None).first()
    if existing_bot_vote is not None and prevent_revote:
        return existing_bot_vote.restaurant

    if date.weekday() == 2:  # Wednesday
        r = Restaurant.query.filter_by(name='Pasta Day').first()
    else:
        latest_restaurants = db.session.query(Restaurant.id).filter(
            Restaurant.id == RestaurantChoice.restaurant_id).filter(
            RestaurantChoice.date >= date - datetime.timedelta(days=2)).filter(
            RestaurantChoice.date < date).all()
        blacklist = set(r[0] for r in latest_restaurants)
        blacklist.add(Restaurant.query.filter_by(name='Pasta Day').first().id)
        active_restaurants = Restaurant.query.filter_by(active=True).all()
        active_restaurants = [r for r in active_restaurants if r.id not in blacklist]
        weights = [r.weight for r in active_restaurants]
        r = random.choices(active_restaurants, weights, k=1)[0]

    weight = 10.0 if (r.name == 'Pasta Day') else 0.1
    voteForRestaurant(r.id, None, date, weight)
    return r


def update_credits(paying_user):
    date = datetime.date.today()
    if is_pasta_day(date):
        paying_user = get_pastabot()

    orders = db.session.query(Dish.price, User).filter(
        DishChoice.dish_id == Dish.id).filter(
        DishChoice.user_id == User.id).filter(
        DishChoice.date == date).filter(
        DishChoice.status == 1).all()

    for price, user in orders:
        transfer_credits(user, paying_user, price, "Lunch order")
    db.session.commit()

def transfer_credits(sending_user, receiving_user, amount_in_cents, comment=None):
    sending_user.credit -= amount_in_cents
    receiving_user.credit += amount_in_cents
    date = datetime.date.today()
    transaction = CreditTransaction(sender_id=sending_user.id, receiver_id=receiving_user.id, amount=amount_in_cents,
                                    date=date, status=1, comment=comment)
    db.session.add(transaction)
    db.session.commit()
    logger.debug(f"Transferred {amount_in_cents} credits from {sending_user.first_name} to {receiving_user.first_name}: {comment if comment is not None else ''}")


def getLeadingRestaurant(date):
    castBotVoteForRestaurant(date, prevent_revote=True) # ensure at least 1 vote
    restaurant_id = db.session.query(RestaurantVote.restaurant_id).filter(
        RestaurantVote.date == date).filter(
        Restaurant.active == True).group_by(
        RestaurantVote.restaurant_id).order_by(
        sqlfunc.sum(RestaurantVote.weight).desc()).first()[0]
    restaurant = Restaurant.query.get(restaurant_id)
    return restaurant


def selectRestaurant(date=None):
    if date is None:
        date = datetime.date.today()
    restaurant = getLeadingRestaurant(date)

    RestaurantChoice.query.filter_by(date=date).delete()
    db.session.add(RestaurantChoice(date=date, restaurant_id=restaurant.id))
    db.session.commit()
    selectDishesRandomly(restaurant, date)
    return restaurant


def selectOrderer(date=None, confirm_sendout=False):
    if date is None:
        date = datetime.date.today()

    # Check if OrdererChoice has already been made
    current_orderer = OrdererChoice.query.filter_by(date=date, status=1).first()
    if current_orderer is not None:
        return current_orderer.user

    # If not => Select a new one based on karma
    potential_users = getUsersWithConfirmedOrder()
    if len(potential_users) == 0:
        return None
    potential_user_ids = set([u.id for u in potential_users])

    user_karma_data = getAllUserKarma() # already sorted by karma in descending order
    for karma, user_dict in user_karma_data[::-1]:
        if user_dict['id'] in potential_user_ids:
            user = User.query.get(user_dict['id'])
            OrdererChoice.query.filter_by(date=date).delete()
            db.session.add(OrdererChoice(user_id=user.id, date=date, status=1 if confirm_sendout else 0))
            db.session.commit()
            return user
    return None

def selectDishesRandomly(restaurant, date=None):
    if date is None:
        date = datetime.date.today()
    active_users = getActiveUsers()
    logger.debug("Restaurant: " + str(restaurant.id))

    DishChoice.query.filter_by(date=date).delete()
    for user in active_users:
        results = db.session.query(Dish.id, UserDishWeight.weight).filter(
            UserDishWeight.user_id == user.id).filter(
            Dish.restaurant_id == restaurant.id).filter(
            Dish.id == UserDishWeight.dish_id).all()
        ids = [r[0] for r in results]
        weights = [r[1] for r in results]
        logger.debug("Ids: " + str(ids))
        dish_id = random.choices(ids, weights, k=1)[0]
        db.session.add(DishChoice(user_id=user.id, dish_id=dish_id, date=date))
    db.session.commit()


# %% Slack communication
def is_valid_slack_request(payload):
    return payload['token'] == app.config['SLACK_REQUEST_TOKEN']


def sendRestaurantOptions(channel_name='lunch'):
    date = datetime.date.today()
    restaurants = getActiveRestaurants()
    leading_restaurant = getLeadingRestaurant(date)
    slack.sendRestaurantOptionsMessage(restaurants, leading_restaurant, channel_name, SLACK_BOT_TOKEN)


def sendLunchProposal(user):
    restaurant = getTodaysRestaurant()

    possible_dishes = getPossibleDishes(user, restaurant)
    proposed_dish = db.session.query(Dish).filter(
        DishChoice.user_id == user.id).filter(
        DishChoice.date == datetime.date.today()).filter(
        Dish.id == DishChoice.dish_id).first()
    return slack.sendLunchOptionsMessage(user, restaurant, possible_dishes, proposed_dish,
                                         app.config['SLACK_BOT_TOKEN'])


def sendLunchProposalToAll():
    active_users = getActiveUsers()
    for user in active_users:
        logger.info(f"Sending lunch-options to {user}")
        print(sendLunchProposal(user))
    return len(active_users)


def sendOrderSummary(responsible_user=None):
    date = datetime.date.today()
    if responsible_user is None:
        responsible_user = selectOrderer(date, confirm_sendout=True)
    if is_pasta_day(date):
        sendOrderSummaryPastaDay(responsible_user)
        logger.info(f"Sent pasta instructions to: {responsible_user.first_name}")
    else:
        orders = db.session.query(Dish, User).filter(
            DishChoice.dish_id == Dish.id).filter(
            DishChoice.user_id == User.id).filter(
            DishChoice.date == date).filter(
            DishChoice.status == 1).order_by(Dish.name).all()
        orders = [(o[0].name, o[1].first_name) for o in orders]
        if len(orders) == 0:
            return
        slack.sendOrderSummary(responsible_user, orders, getTodaysRestaurant().name, SLACK_BOT_TOKEN)
        logger.info(f"Sent lunch order summary to: {responsible_user.first_name}")
    update_credits()


def sendOrderSummaryPastaDay(responsible_user):
    joining_users = db.session.query(User).filter(
        User.id == DishChoice.user_id).filter(
        DishChoice.date == datetime.date.today()).filter(
        DishChoice.status == 1).all()
    pasta_amount = int(220 * len(joining_users))
    slack.sendOrderSummaryPasta(responsible_user, joining_users, pasta_amount, SLACK_BOT_TOKEN)

#%% Actions in response to slack requests
def action_subscribe(payload, user):
    user.active = True
    db.session.commit()
    logger.info(f"User {user.get_full_name()} has been activated.")
    slack.sendSubscribeMessage(user, SLACK_BOT_TOKEN)


def action_unsubscribe(payload, user):
    slack.sendUnsubscribeMessage(user, SLACK_BOT_TOKEN)
    user.active = False
    db.session.commit()
    logger.info(f"User {user.get_full_name()} has been deactivated.")


def action_select_dish(payload, user):
    dish_id = int(payload['state']['values']['dish_selection_section']['static_select-action']['selected_option']["value"])
    setUserChoice(user.id, dish_id)

    orderer_choice = OrdererChoice.query.filter_by(date=datetime.date.today(), status=1).first()
    if orderer_choice is None:
        slack.sendLunchConfirmation(user, Dish.query.get(dish_id).name, SLACK_BOT_TOKEN)
    else:
        slack.sendTooLateMessage(user, orderer_choice.user, SLACK_BOT_TOKEN)


def action_decline_dish(payload, user):
    setUserChoice(user.id, None)
    slack.sendLunchNoOrderConfirmation(user, SLACK_BOT_TOKEN)


def action_cast_restaurant_upvote(payload, user):
    restaurant_id = int(payload['state']['values']['voting']['ignore_select_restaurant']['selected_option']["value"])
    voteForRestaurant(restaurant_id, user.id)
    restaurant = Restaurant.query.get(restaurant_id)
    logger.info(f"{user.first_name} voted for {restaurant.name}")
    slack.sendVoteConfirmation(user, "+1", restaurant.name, SLACK_BOT_TOKEN)


def action_cast_restaurant_downvote(payload, user):
    restaurant_id = int(payload['state']['values']['voting']['ignore_select_restaurant']['selected_option']["value"])
    voteForRestaurant(restaurant_id, user.id, weight=-1)
    restaurant = Restaurant.query.get(restaurant_id)
    logger.info(f"{user.first_name} voted against {restaurant.name}")
    slack.sendVoteConfirmation(user, "-1", restaurant.name, SLACK_BOT_TOKEN)


ACTION_CALLBACKS = dict(subscribe=action_subscribe, unsubscribe=action_unsubscribe, select_dish=action_select_dish,
                        decline_dish=action_decline_dish, cast_restaurant_upvote=action_cast_restaurant_upvote,
                        cast_restaurant_downvote=action_cast_restaurant_downvote)

def savePayloadForDebugging(payload):
    with open('/data/request.json', 'w') as f:
        json.dump(payload, f, indent=4)

# %% Views
@app.route('/test', methods=['GET', 'POST'])
@basic_auth.required
def test():
    if flask.request.method == 'POST':
        if 'choose_restaurant' in flask.request.form.keys():
            selectRestaurant()
            return flask.redirect('/')
        elif 'choose_5_restaurants' in flask.request.form.keys():
            proposeRestaurantSchedule()
            return flask.redirect('/restaurant_schedule')
        elif 'send_slack' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            r = sendLunchProposal(user)
            return r.text
        elif 'send_pasta_instructions_michael' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            r = sendOrderSummaryPastaDay(user)
        elif 'send_active' in flask.request.form.keys():
            n = sendLunchProposalToAll()
            flask.flash(f"Messages sent to {n} people")
        elif 'send_confirmation' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            slack.sendLunchConfirmation(user, 'TestDish', SLACK_BOT_TOKEN)
        elif 'send_order_summary_michael' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            sendOrderSummary(user)
        elif 'send_slack_lukas' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Liehr').first()
            sendLunchProposal(user)
        elif 'send_order_summary' in flask.request.form.keys():
            sendOrderSummary()
        elif 'update_dish_weights' in flask.request.form.keys():
            updateDishWeights()
        elif 'send_restaurant_options_michael' in flask.request.form.keys():
            sendRestaurantOptions('test')
        elif 'send_restaurant_options' in flask.request.form.keys():
            sendRestaurantOptions()
        else:
            return "Unknown request"
    return flask.render_template('test.html')


@app.route('/restaurant_votes')
def restaurant_votes():
    results = db.session.query(RestaurantVote.restaurant_id,
                              sqlfunc.sum(RestaurantVote.weight)).filter(
        RestaurantVote.date == datetime.date.today()).group_by(
        RestaurantVote.restaurant_id).order_by(sqlfunc.sum(RestaurantVote.weight).desc()).all()
    logger.debug(str(results))

    restaurants = [dict(name=Restaurant.query.get(r[0]).name, votes=r[1]) for r in results]
    return flask.render_template("restaurant_votes.html", restaurants=restaurants)


@app.route('/')
# No basic auth for index view, since no sensitive data (beyond names)
def index():
    restaurant = getTodaysRestaurant()
    if restaurant is None:
        return flask.redirect('/restaurant_votes')
        # return flask.render_template('index_undecided.html')

    choices = db.session.query(User, DishChoice
                               ).filter(User.active == True
                                        ).filter(User.id == DishChoice.user_id
                                                 ).filter(DishChoice.date == datetime.date.today()).all()

    table_rows = []
    confirmed_ids = set()
    for user, choice in choices:
        if choice.status < 2:
            dish_name = choice.dish.name
        else:
            dish_name = ""
        table_rows.append(dict(name=user.first_name + " " + user.last_name, dish=dish_name, status=choice.status))
        confirmed_ids.add(user.id)
    table_rows = sorted(table_rows, key=lambda r: (r['status'], r['dish']))

    return flask.render_template('index.html', table_rows=table_rows,
                                 restaurant=restaurant.name)


@app.route('/karma')
# No basic auth right now for UX-reasons
def karma():
    user_data = getAllUserKarma()
    return flask.render_template('karma.html', user_data=user_data)


@app.route('/profile/<user_id>', methods=['GET', 'POST'])
# No basic auth right now for UX-reasons
def profile(user_id):
    restaurant = getTodaysRestaurant()
    if restaurant is None:
        return flask.render_template('index_undecided.html')
    user = User.query.get(user_id)
    if flask.request.method == 'POST':
        dish_name = flask.request.form['dish_name']
        dish_price = flask.request.form['dish_price'] * 100
        if len(dish_name) > 0:
            addDish(dish_name, dish_price, user, restaurant, confirm_choice=True)
            flask.flash(f"Added dish {dish_name} and selected it for today")
            slack.sendLunchConfirmation(user, dish_name, SLACK_BOT_TOKEN)
    return flask.render_template('profile.html', user_name=user.first_name, restaurant=restaurant.name)


# No basic auth right now for UX-reasons: Should probably be changed at some point
@app.route('/transaction', methods=['GET', 'POST'])
def transaction():
    if flask.request.method == 'POST':
        sender = User.query.get(flask.request.form['user1'])
        comment = flask.request.form['comment']
        amount = float(flask.request.form['amount']) * 100
        if flask.request.form['form_type'] == 'pasta_purchase':
            receiver = get_pastabot()
        elif flask.request.form['form_type'] == 'money_transfer':
            receiver = User.query.get(flask.request.form['user2'])
        else:
            raise ValueError("Invalid form type for transaction")

        # This seems backwards but is correct: The one sending the money, is receivng the credits
        transfer_credits(receiver, sender, amount, comment)
        flask.flash(f"Transferred {amount/100:.2f} credits from {receiver.first_name} to {sender.first_name}. Your new credit balance is now {sender.credit/100:.2f} EUR")

    user_list = User.query.all()
    user_list = [(u.id, u.get_full_name()) for u in user_list]
    return flask.render_template('transaction.html', users=user_list)


@app.route('/api', methods=['POST'])
# No basic auth, because needs to be reachable by slack, but checking for valid token
def api():
    payload = json.loads(flask.request.values['payload'])
    savePayloadForDebugging(payload)
    if not is_valid_slack_request(payload):
        return "Not authorized", 401
    user = addUserIfNotExists(payload['user'])
    logger.info(f"Received api request from user {user.get_full_name()}")
    for action in payload.get('actions', ()):
        action_id = action['action_id']
        logger.info(f"User: {user.get_full_name()}, Action: {action_id}")
        callback = ACTION_CALLBACKS.get(action_id, None)
        if callback is not None:
            result = callback(payload, user)
            result = "" if result is None else result
            return result
    return ""


if __name__ == '__main__':
    app.run(debug=True, port=80)
