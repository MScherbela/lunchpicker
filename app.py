import flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
import slack
import json
import logging
import datetime
import random
import sqlalchemy.sql.functions
from flask_basicauth import BasicAuth
from werkzeug.exceptions import HTTPException
from flask_apscheduler import APScheduler

try:
    logging.basicConfig(filename='/data/lunchbot.log', level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
except FileNotFoundError:
    logging.basicConfig(filename='lunchbot.log', level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

app = flask.Flask(__name__)
app.config.from_pyfile('config.py')
app.config.from_pyfile('instance/config.py')
db = SQLAlchemy(app)
basic_auth = BasicAuth(app)

SLACK_BOT_TOKEN = app.config['SLACK_BOT_TOKEN']

scheduler = APScheduler(app=app)
scheduler.start()

class UserDishWeight(db.Model):
    __tablename__ = 'user_dish_weight'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), primary_key=True)
    weight = db.Column(db.Float, default=1.0)

class Restaurant(db.Model):
    __tablename__ = 'restaurant'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Float, default=1.0)
    choices = db.relationship('RestaurantChoice', backref='restaurant')
    dishes = db.relationship('Dish', backref='restaurant')
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return self.name

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))
    slack_id = db.Column(db.String(256))
    active = db.Column(db.Boolean, default=True)
    vegetarian = db.Column(db.Boolean, default=False)

    def get_full_name(self):
        return self.first_name + " " + self.last_name

    def __repr__(self):
        return f"{self.first_name} {self.last_name}"

class Dish(db.Model):
    __tablename__ = 'dish'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    choices = db.relationship('DishChoice', backref='dish')
    vegetarian = db.Column(db.Boolean, default=False)
    is_default = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"{self.name} ({self.restaurant})"

class DishChoice(db.Model):
    __tablename__ = 'dish_choice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'))
    status = db.Column(db.Integer, default=0)

class RestaurantChoice(db.Model):
    __tablename__ = 'restaurant_choice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)

    def __repr__(self):
        return f"<RestaurantChoice: {self.date}, {self.restaurant_id}>"

class OrdererChoice(db.Model):
    __table_name__ = 'orderer_choice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<OrdererChoice: {self.date}, {self.user_id}; status: {self.status}>"

class AuthException(HTTPException):
    def __init__(self, message):
        super().__init__(message, flask.Response(
            "You could not be authenticated. Please refresh the page.", 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'} ))

class ProtectedModelView(ModelView):
    def is_accessible(self):
        if not basic_auth.authenticate():
            raise AuthException('Not authenticated.')
        return True

    def inaccessible_callback(self, name, **kwargs):
        return flask.redirect(basic_auth.challenge())

class ProtectedAdminIndexView(AdminIndexView):
    def is_accessible(self):
        if not basic_auth.authenticate():
            raise AuthException('Not authenticated.')
        return True

    def inaccessible_callback(self, name, **kwargs):
        return flask.redirect(basic_auth.challenge())

class UserView(ProtectedModelView):
    column_hide_backrefs = False
    column_list = ('first_name', 'last_name', 'dishes')

class DishView(ProtectedModelView):
    column_hide_backrefs = False
    column_list = ('name', 'restaurant', 'users')

class RestaurantView(ProtectedModelView):
    column_hide_backrefs = False
    column_list = ('name', 'url', 'description', 'rating', 'dishes')

admin = Admin(app, name='lunch', template_mode='bootstrap3', index_view=ProtectedAdminIndexView())
admin.add_view(UserView(User, db.session))
admin.add_view(RestaurantView(Restaurant, db.session))
admin.add_view(DishView(Dish, db.session))
admin.add_view(ProtectedModelView(DishChoice, db.session))
admin.add_view(ProtectedModelView(RestaurantChoice, db.session))
admin.add_view(ProtectedModelView(OrdererChoice, db.session))
admin.add_view(ProtectedModelView(UserDishWeight, db.session))

@scheduler.task('cron', id='heartbeat', minute=30, hour=8)
def hearbeatTask():
    logger.debug("I'm still alive!")

@scheduler.task('cron', id='send_lunch_options', minute=45, hour=10, day_of_week='mon,tue,wed,thu,fri')
def sendLunchOptionsTask():
    sendLunchOptions()

@scheduler.task('cron', id='send_order_summary', minute=15, hour=11, day_of_week='mon,tue,wed,thu,fri')
def sendOrderSummaryTask():
    sendOrderSummary()
    updateDishWeights()

@scheduler.task('cron', id='propose_restaurant_schedule', minute=0, hour=4, day_of_week="Sun")
def proposeRestaurantScheduleTask():
    proposeRestaurantSchedule()

def updateDishWeights():
    """Calculate dish preferences based on order history"""
    pass

def sendLunchOptions():
    active_users = getActiveUsers()
    for user in active_users:
        logger.info(f"Sending lunch-options to {user}")
        print(sendLunchProposal(user))
    return len(active_users)

def proposeRestaurantSchedule():
    for d in range(7):
        date = datetime.date.today() + datetime.timedelta(days=d)
        if date.weekday() < 5: # Mo-Fr
            selectRestaurantRandomly(date)

def setRestaurantSchedule(date, restaurant_id):
    choice = RestaurantChoice.query.filter_by(date=date).first()
    if (choice is not None) and choice.restaurant_id == restaurant_id:
        return  # Already same restaurant selected; nothing to do
    if choice is None:
        choice = RestaurantChoice(date=date, restaurant_id=restaurant_id)
        db.session.add(choice)
    else:
        choice.restaurant_id = restaurant_id
    db.session.commit()
    selectDishesRandomly(Restaurant.query.get(restaurant_id), date)

def sendOrderSummary(responsible_user=None):
    date = datetime.date.today()
    orders = db.session.query(Dish, User).filter(
        DishChoice.dish_id == Dish.id).filter(
        DishChoice.user_id == User.id).filter(
        DishChoice.date == date).filter(
        DishChoice.status == 1).order_by(Dish.name).all()
    orders = [(o[0].name, o[1].first_name) for o in orders]
    if len(orders) == 0:
        return

    if responsible_user is None:
        responsible_user = selectOrderer(date)
    slack.sendOrderSummary(responsible_user, orders, getTodaysRestaurant().name, SLACK_BOT_TOKEN)
    logger.info(f"Sent lunch order summary to: {responsible_user.first_name}")

def getActiveUsers():
    return User.query.filter_by(active=True).all()

def getUsersWithConfirmedOrder(date=None):
    if date is None:
        date = datetime.date.today()
    return db.session.query(User).filter(
        User.id == DishChoice.user_id).filter(
        DishChoice.date==date).filter(
        DishChoice.status == 1).all()

def getActiveRestaurants():
    return Restaurant.query.filter_by(active=True).all()

def getTodaysRestaurant(date=None):
    if date is None:
        date = datetime.date.today()
    restaurant_choice = RestaurantChoice.query.filter_by(date=date).first()
    if restaurant_choice is None:
        return selectRestaurantRandomly(date)
    else:
        return restaurant_choice.restaurant

def is_valid_slack_request(payload):
    return payload['token'] == app.config['SLACK_REQUEST_TOKEN']


def selectOrderer(date=None):
    if date is None:
        date = datetime.date.today()
    potential_users = getUsersWithConfirmedOrder()
    if len(potential_users) == 0:
        return None

    user_choices = db.session.query(User.id, sqlalchemy.sql.functions.count(DishChoice.date)).filter(
        User.id == DishChoice.user_id).filter(
        DishChoice.date < date).filter(
        DishChoice.status == 1).group_by(User.id).all()
    user_choices = {r[0]:r[1] for r in user_choices}
    user_orders = db.session.query(User.id, sqlalchemy.sql.functions.count(OrdererChoice.date)).filter(
        User.id == OrdererChoice.user_id).filter(
        OrdererChoice.date < date).group_by(User.id).all()
    user_orders = {r[0]:r[1] for r in user_orders}

    highest_user = None
    highest_ratio = 0.0
    for user in getActiveUsers():
        ratio = user_choices.get(user.id, 0) / user_orders.get(user.id, 0.1)
        if ratio >= highest_ratio:
            highest_user = user
            highest_ratio = ratio

    OrdererChoice.query.filter_by(date=date).delete()
    db.session.add(OrdererChoice(user_id=highest_user.id, date=date))
    db.session.commit()
    return highest_user

def selectRestaurantRandomly(date=None):
    if date is None:
        date = datetime.date.today()
    if date.weekday() == 2: # Wednesday
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

    RestaurantChoice.query.filter_by(date=date).delete()
    db.session.add(RestaurantChoice(date=date, restaurant_id=r.id))
    db.session.commit()
    selectDishesRandomly(r, date)
    return r

def confirmUserChoice(user_id, dish_id):
    today = datetime.date.today()
    DishChoice.query.filter_by(date=today, user_id=user_id).delete()
    db.session.add(DishChoice(date=today, user_id=user_id, dish_id=dish_id, status=2 if dish_id is None else 1))
    db.session.commit()

def getPossibleDishes(user, restaurant):
    return db.session.query(Dish).filter(UserDishWeight.user_id==user.id).filter(Dish.restaurant_id == restaurant.id).all()

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

def sendLunchProposal(user):
    restaurant = getTodaysRestaurant()

    possible_dishes = getPossibleDishes(user, restaurant)
    proposed_dish = db.session.query(Dish).filter(
        DishChoice.user_id == user.id).filter(
        DishChoice.date == datetime.date.today()).filter(
        Dish.id == DishChoice.dish_id).first()
    return slack.sendLunchOptionsMessage(user, restaurant, possible_dishes, proposed_dish, app.config['SLACK_BOT_TOKEN'])

@app.route('/test', methods=['GET', 'POST'])
@basic_auth.required
def test():
    if flask.request.method == 'POST':
        if 'choose_restaurant' in flask.request.form.keys():
            selectRestaurantRandomly()
            return flask.redirect('/')
        elif 'choose_5_restaurants' in flask.request.form.keys():
            proposeRestaurantSchedule()
            return flask.redirect('/restaurant_schedule')
        elif 'send_slack' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            r = sendLunchProposal(user)
            return r.text
        elif 'send_active' in flask.request.form.keys():
            n = sendLunchOptions()
            flask.flash(f"Messages sent to {n} people")
        elif 'send_confirmation' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            slack.sendLunchConfirmation(user, 'TestDish', SLACK_BOT_TOKEN)
        elif 'send_order_summary_michael' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            sendOrderSummary(user)
        elif 'send_order_summary' in flask.request.form.keys():
            sendOrderSummary()
        else:
            return "Unknown request"
    return flask.render_template('test.html')

@app.route('/schedule', methods=['GET', 'POST'])
@basic_auth.required
def schedule():
    if flask.request.method == 'POST':
        form = flask.request.form
        date = datetime.date.fromisoformat(form['date'])
        setRestaurantSchedule(date, int(form['restaurant']))

    restaurant_choices = RestaurantChoice.query.order_by(RestaurantChoice.date).all()
    restaurants = getActiveRestaurants()

    table_rows = []
    for choice in restaurant_choices:
        restaurant_options = [dict(id=r.id, name=r.name, selected=(r.id == choice.restaurant_id)) for r in restaurants]
        table_rows.append(dict(date=choice.date, restaurants=restaurant_options))

    return flask.render_template("schedule.html", table_rows=table_rows)

@app.route('/')
# No basic auth for index view, since no sensitive data (beyond names)
def index():
    restaurant = getTodaysRestaurant()

    choices = db.session.query(User, DishChoice
                     ).filter(User.active==True
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

@app.route('/profile/<user_id>', methods=['GET', 'POST'])
# No basic auth right now for UX-reasons
def profile(user_id):
    restaurant = getTodaysRestaurant()
    user = User.query.get(user_id)
    if flask.request.method == 'POST':
        dish_name = flask.request.form['dish_name']
        if len(dish_name) > 0:
            dish = Dish(name=dish_name, restaurant_id=restaurant.id)
            db.session.add(dish)
            db.session.commit()
            confirmUserChoice(user_id, dish.id)
            flask.flash(f"Added dish {dish_name} and selected it for today")
            slack.sendLunchConfirmation(user, dish_name, SLACK_BOT_TOKEN)
    return flask.render_template('profile.html', user_name = user.first_name, restaurant=restaurant.name)

@app.route('/api', methods=['POST'])
# No basic auth, because needs to be reachable by slack, but checking for valid token
def api():
    payload = json.loads(flask.request.values['payload'])
    if not is_valid_slack_request(payload):
        return "Not authorized", 401
    result = slack.parseSlackRequestPayload(payload)
    user = User.query.filter_by(slack_id=result['user']).first()
    logger.info(f"Received api request from user {user.get_full_name()}")
    if result['button'] == 'yes':
        confirmUserChoice(user.id, result['dish_id'])
        slack.sendLunchConfirmation(user, Dish.query.get(result['dish_id']).name, SLACK_BOT_TOKEN)
    elif result['button'] == 'no':
        confirmUserChoice(user.id, None)
        slack.sendLunchNoOrderConfirmation(user, SLACK_BOT_TOKEN)
    return ""

if __name__ == '__main__':
    app.run(debug=True, port=80)
