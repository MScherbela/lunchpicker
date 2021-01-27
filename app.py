import flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import slack
import json
import logging

logging.basicConfig(filename='/data/lunchbot.log', level=logging.DEBUG)
logger = logging.getLogger()

app = flask.Flask(__name__)
app.config.from_pyfile('config.py')
app.config.from_pyfile('instance/config.py')
db = SQLAlchemy(app)
admin = Admin(app, name='lunch', template_mode='bootstrap3')

user_dishes = db.Table('user_dishes',
                       db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                       db.Column('dish_id', db.Integer, db.ForeignKey('dish.id'), primary_key=True))

class Restaurant(db.Model):
    __tablename__ = 'restaurant'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=False)
    description = db.Column(db.Text)
    rating = db.Column(db.Float)
    dishes = db.relationship('Dish', backref='restaurant')

    def __repr__(self):
        return self.name

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))
    dishes = db.relationship('Dish', secondary=user_dishes, lazy='subquery', backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f"{self.first_name} {self.last_name}"

class Dish(db.Model):
    __tablename__ = 'dish'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    choices = db.relationship('DishChoice', backref='dish')
    vegetarian = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"{self.name} ({self.restaurant})"

class DishChoice(db.Model):
    __tablename__ = 'dish_choice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=False)
    status = db.Column(db.Integer, default=0)

class UserView(ModelView):
    column_hide_backrefs = False
    column_list = ('first_name', 'last_name', 'dishes')

class DishView(ModelView):
    column_hide_backrefs = False
    column_list = ('name', 'restaurant', 'users')

class RestaurantView(ModelView):
    column_hide_backrefs = False
    column_list = ('name', 'url', 'description', 'rating', 'dishes')

# admin.add_view(UserView(User, db.session))
# admin.add_view(RestaurantView(Restaurant, db.session))
# admin.add_view(DishView(Dish, db.session))
# admin.add_view(ModelView(DishChoice, db.session))

def is_valid_slack_request(payload):
    return payload['token'] == app.config['SLACK_REQUEST_TOKEN']

@app.route('/', methods=['GET', 'POST'])
def index():
    if flask.request.method == 'POST':
        r = slack.sendLunchOptionsMessage(app.config['SLACK_BOT_TOKEN'])
        return r.text
    else:
        return flask.render_template('index.html')

@app.route('/api', methods=['POST'])
def api():
    payload = json.loads(flask.request.values['payload'])
    if not is_valid_slack_request(payload):
        return 401
    button_value = slack.getSlackRequestButtonValue(payload)
    if button_value is None:
        logger.info("Not a button request")
    else:
        logger.info("Button: "+button_value)

    with open('/data/requests.txt', 'w') as f:
       f.write(json.dumps(payload, indent=4))
    return ""

if __name__ == '__main__':
    app.run(debug=True, port=80)
