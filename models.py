from extensions import db


class UserDishWeight(db.Model):
    __tablename__ = 'user_dish_weight'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), primary_key=True)
    user = db.relationship('User')
    dish = db.relationship('Dish')
    weight = db.Column(db.Float, default=1.0)


class Restaurant(db.Model):
    __tablename__ = 'restaurant'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Float, default=1.0)
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
    user = db.relationship('User')
    dish = db.relationship('Dish')
    status = db.Column(db.Integer, default=0)


class RestaurantChoice(db.Model):
    __tablename__ = 'restaurant_choice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    restaurant = db.relationship('Restaurant')

    def __repr__(self):
        return f"<RestaurantChoice: {self.date}, {self.restaurant_id}>"


class OrdererChoice(db.Model):
    __table_name__ = 'orderer_choice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', )
    status = db.Column(db.Integer, default=0) #0: defined but not yet communicated; 1: summary already sent

    def __repr__(self):
        return f"<OrdererChoice: {self.date}, {self.user_id}; status: {self.status}>"


class RestaurantVote(db.Model):
    __tablename__ = 'restaurant_vote'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    restaurant = db.relationship('Restaurant')
    user = db.relationship('User')
    weight = db.Column(db.Float, default=1.0)
