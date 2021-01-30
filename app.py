import flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import slack
import json
import logging
from datetime import date
import random

try:
    logging.basicConfig(filename='/data/lunchbot.log', level=logging.DEBUG)
except FileNotFoundError:
    logging.basicConfig(filename='lunchbot.log', level=logging.DEBUG)
logger = logging.getLogger()

app = flask.Flask(__name__)
app.config.from_pyfile('config.py')
app.config.from_pyfile('instance/config.py')
db = SQLAlchemy(app)
admin = Admin(app, name='lunch', template_mode='bootstrap3')

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

class UserView(ModelView):
    column_hide_backrefs = False
    column_list = ('first_name', 'last_name', 'dishes')

class DishView(ModelView):
    column_hide_backrefs = False
    column_list = ('name', 'restaurant', 'users')

class RestaurantView(ModelView):
    column_hide_backrefs = False
    column_list = ('name', 'url', 'description', 'rating', 'dishes')

admin.add_view(UserView(User, db.session))
admin.add_view(RestaurantView(Restaurant, db.session))
admin.add_view(DishView(Dish, db.session))
admin.add_view(ModelView(DishChoice, db.session))
admin.add_view(ModelView(RestaurantChoice, db.session))
admin.add_view(ModelView(UserDishWeight, db.session))

def is_valid_slack_request(payload):
    return payload['token'] == app.config['SLACK_REQUEST_TOKEN']

def selectRestaurantRandomly():
    today = date.today()
    if today.weekday() == 2: # Wednesday
        r = Restaurant.query.filter_by(name='Pasta Day').first()
    else:
        active_restaurants = Restaurant.query.filter_by(active=True).all()
        weights = [r.weight for r in active_restaurants]
        r = random.choices(active_restaurants, weights, k=1)[0]
    RestaurantChoice.query.filter_by(date=today).delete()
    db.session.add(RestaurantChoice(date=today, restaurant_id=r.id))
    db.session.commit()
    selectDishesRandomly(r)
    return active_restaurants

def confirmUserChoice(user_id, dish_id):
    today = date.today()
    DishChoice.query.filter_by(date=today, user_id=user_id).delete()
    db.session.add(DishChoice(date=today, user_id=user_id, dish_id=dish_id, status=2 if dish_id is None else 1))
    db.session.commit()

def getPossibleDishes(user, restaurant):
    return db.session.query(Dish).filter(UserDishWeight.user_id==user.id).filter(Dish.restaurant_id == restaurant.id).all()

def selectDishesRandomly(restaurant):
    today = date.today()
    active_users = User.query.filter_by(active=True).all()
    logger.debug("Restaurant: " + str(restaurant.id))

    DishChoice.query.filter_by(date=today).delete()
    for user in active_users:
        results = db.session.query(Dish.id, UserDishWeight.weight).filter(
            UserDishWeight.user_id == user.id).filter(
            Dish.restaurant_id == restaurant.id).filter(
            Dish.id == UserDishWeight.dish_id).all()
        ids = [r[0] for r in results]
        weights = [r[1] for r in results]
        logger.debug("Ids: " + str(ids))
        dish_id = random.choices(ids, weights, k=1)[0]
        db.session.add(DishChoice(user_id=user.id, dish_id=dish_id, date=today))
    db.session.commit()

@app.route('/test', methods=['GET', 'POST'])
def test():
    if flask.request.method == 'POST':
        if 'choose_restaurant' in flask.request.form.keys():
            active_restaurants = selectRestaurantRandomly()
            #return str(active_restaurants)
            return flask.redirect('/')
        elif 'send_slack' in flask.request.form.keys():
            user = User.query.filter_by(last_name='Scherbela').first()
            r = sendLunchProposal(user)
            return r.text
        else:
            return "Unknown request"
    else:
        return flask.render_template('sendMessage.html')

def sendLunchProposal(user):
    today = date.today()
    restaurant = RestaurantChoice.query.filter_by(date=today).first().restaurant

    possible_dishes = getPossibleDishes(user, restaurant)
    proposed_dish = db.session.query(Dish).filter(
        DishChoice.user_id == user.id).filter(
        DishChoice.date == today).filter(
        Dish.id == DishChoice.dish_id).first()

    return slack.sendLunchOptionsMessage(user, restaurant, possible_dishes, proposed_dish, app.config['SLACK_BOT_TOKEN'])


@app.route('/')
def index():
    restaurant_choice = RestaurantChoice.query.filter_by(date=date.today()).first()
    if restaurant_choice is None:
        return flask.render_template('index.html', table_rows=[], restaurant="")

    choices = db.session.query(User, DishChoice
                     ).filter(User.active==True
                     ).filter(User.id == DishChoice.user_id
                     ).filter(DishChoice.date == date.today()).all()

    table_rows = []
    confirmed_ids = set()
    for user, choice in choices:
        table_rows.append(dict(name=user.first_name + " " + user.last_name, dish=choice.dish.name, status=choice.status))
        confirmed_ids.add(user.id)
    table_rows = sorted(table_rows, key=lambda r: (r['status'], r['dish']))

    return flask.render_template('index.html', table_rows=table_rows,
                                 restaurant=restaurant_choice.restaurant.name)

@app.route('/profile/<user_id>', methods=['GET', 'POST'])
def profile(user_id):
    restaurant = RestaurantChoice.query.filter_by(date=date.today()).first().restaurant
    user = User.query.get(user_id)
    if flask.request.method == 'POST':
        dish_name = flask.request.form['dish_name']
        if len(dish_name) > 0:
            dish = Dish(name=dish_name, restaurant_id=restaurant.id)
            db.session.add(dish)
            db.session.commit()
            confirmUserChoice(user_id, dish.id)
            flask.flash(f"Added dish {dish_name} and selected it for today")
    return flask.render_template('profile.html', user_name = user.first_name, restaurant=restaurant.name)

@app.route('/api', methods=['POST'])
def api():
    payload = json.loads(flask.request.values['payload'])
    if not is_valid_slack_request(payload):
        return 401
    result = slack.parseSlackRequestPayload(payload)
    if result['button'] == 'yes':
        user = User.query.filter_by(slack_id=result['user']).first()
        confirmUserChoice(user.id, result['dish_id'])
    elif result['button'] == 'no':
        user = User.query.filter_by(slack_id=result['user']).first()
        confirmUserChoice(user.id, None)

    logger.debug(json.dumps(payload, indent=4))
    return ""

if __name__ == '__main__':
    app.run(debug=True, port=80)
