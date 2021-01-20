import flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = flask.Flask(__name__)
app.config.from_pyfile('config.py')
app.config.from_pyfile('instance/config.py')
db = SQLAlchemy(app)
admin = Admin(app, name='lunch', template_mode='bootstrap3')

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
    dishes = db.relationship('Dish', backref='user')

    def __repr__(self):
        return f"{self.first_name} {self.last_name}"

class Dish(db.Model):
    __tablename__ = 'dish'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    choices = db.relationship('DishChoice', backref='dish')

    def __repr__(self):
        return f"{self.name}; {self.restaurant}, {self.user}"

class DishChoice(db.Model):
    __tablename__ = 'dish_choice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=False)

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Restaurant, db.session))
admin.add_view(ModelView(Dish, db.session))
admin.add_view(ModelView(DishChoice, db.session))

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/profile/<user_id>')
def profile(user_id):
    restaurants = Restaurant.query.all()
    data = []
    for r in restaurants:
        dishes = Dish.query.filter_by(user_id=user_id, restaurant_id=r.id).all()
        data.append((r.name, [d.name for d in dishes]))
    return flask.render_template('profile.html', restaurants=data)

if __name__ == '__main__':
    app.run()
