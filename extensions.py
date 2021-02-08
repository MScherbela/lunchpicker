import flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException
from flask_basicauth import BasicAuth
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_apscheduler import APScheduler

#%% Extensions
db = SQLAlchemy()
basic_auth = BasicAuth()
scheduler = APScheduler()

#%% Flask Admin Views
from models import *

class AuthException(HTTPException):
    def __init__(self, message):
        super().__init__(message, flask.Response(
            "You could not be authenticated. Please refresh the page.", 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}))

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


admin = Admin(None, name='lunch', template_mode='bootstrap3', index_view=ProtectedAdminIndexView())

def add_admin_views():
    admin.add_view(UserView(User, db.session))
    admin.add_view(RestaurantView(Restaurant, db.session))
    admin.add_view(DishView(Dish, db.session))
    admin.add_view(ProtectedModelView(DishChoice, db.session))
    admin.add_view(ProtectedModelView(RestaurantChoice, db.session))
    admin.add_view(ProtectedModelView(OrdererChoice, db.session))
    admin.add_view(ProtectedModelView(UserDishWeight, db.session))
