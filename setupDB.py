from app import db
import os
import json
os.remove('lunch.db')
db.create_all()
from app import User, Restaurant, Dish, UserDishWeight

def addRestaurant(name, default_dish, weight=1.0, active=True):
    r = Restaurant(name=name, weight=weight, active=active)
    db.session.add(r)
    db.session.commit()
    d = Dish(name=default_dish, restaurant_id=r.id, is_default=True)
    db.session.add(d)
    db.session.commit()

with open('members.json') as f:
    member_data = json.load(f)

def addUser(first_name, last_name, active=False):
    for m in member_data['members']:
        if 'real_name' not in m:
            continue
        if m['real_name'] == first_name + ' ' + last_name:
            u = User(first_name=first_name, last_name=last_name,slack_id=m['id'], active=active)
            db.session.add(u)
            db.session.commit()

            default_dishes = Dish.query.filter_by(is_default=True).all()
            for d in default_dishes:
                db.session.add(UserDishWeight(user_id=u.id, dish_id=d.id, weight=1.0))
            db.session.commit()
            break
    else:
        print(f"Did not find user: {first_name} {last_name}")

addRestaurant('Oishi', 'Ricebowl: Red Curry Tofu + Misosuppe', weight=2.0)
addRestaurant('Bio Frische', 'Dal Makhni')
addRestaurant('Fladerei', 'Tagesfladen', active=False)
addRestaurant('Pasta Day', 'Unlimited Pasta', active=False)
addRestaurant('Sägewerk', 'Pizza Margharita', weight=0.5)
addRestaurant('Pizzeria Riva', 'Pizza Margharita', weight=0.5)

addUser('Michael', 'Scherbela', True)
addUser('Leon', 'Gerard')
addUser('Pavol', 'Harar')
addUser('Julius', 'Berner')
addUser('Lukas', 'Liehr')

results = db.session.query(User, Dish).filter(
    User.active == True).filter(
    User.id == UserDishWeight.user_id).filter(
    UserDishWeight.dish_id == Dish.id).filter(
    Dish.id == Restaurant.id).filter(
    Restaurant.active == True).all()

for r in results:
    print(r)


