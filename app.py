from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.config.from_pyfile('instance/config.py')
db = SQLAlchemy(app)
admin = Admin(app, name='lunch', template_mode='bootstrap3')

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=False)
    description = db.Column(db.Text)
    rating = db.Column(db.Float)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Restaurant, db.session))

@app.route('/')
def hello_world():
    return 'Hello World!'

if __name__ == '__main__':
    app.run()
