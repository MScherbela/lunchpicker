import flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

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

admin.add_view(UserView(User, db.session))
admin.add_view(RestaurantView(Restaurant, db.session))
admin.add_view(DishView(Dish, db.session))
admin.add_view(ModelView(DishChoice, db.session))

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/profile/<user_id>')
def profile(user_id):
    restaurants = Restaurant.query.all()
    data = []
    user = User.query.get(user_id)
    liked_dishes = set(user.dishes)
    for r in restaurants:
        restaurant_data = dict(name=r.name, dishes=[])
        dishes = Dish.query.filter_by(restaurant_id=r.id).all()
        liked = [d in liked_dishes for d in dishes]
        for d, l in zip(dishes, liked):
            restaurant_data['dishes'].append((l, d.name, d.vegetarian))
        restaurant_data['dishes'] = sorted(restaurant_data['dishes'], reverse=True)
        data.append(restaurant_data)
    return flask.render_template('profile.html', restaurants=data)

if __name__ == '__main__':
    app.run(debug=True)
