from app import db, proposeRestaurantSchedule, proposeOrdererSchedule
import os
import json
if os.path.isfile('/data/lunch.db'):
    os.remove('/data/lunch.db')
db.create_all()
from app import User, Restaurant, Dish, UserDishWeight

def addRestaurant(name, default_dishes, weight=1.0, active=True):
    r = Restaurant(name=name, weight=weight, active=active)
    db.session.add(r)
    db.session.commit()
    for name, veg in default_dishes:
        d = Dish(name=name, restaurant_id=r.id, vegetarian=veg, is_default=True)
    db.session.add(d)
    db.session.commit()

with open('members.json') as f:
    member_data = json.load(f)

def addUser(first_name, last_name, vegetarian, active=False):
    for m in member_data['members']:
        if 'real_name' not in m:
            continue
        if m['real_name'] == first_name + ' ' + last_name:
            u = User(first_name=first_name, last_name=last_name,slack_id=m['id'], vegetarian=vegetarian, active=active)
            db.session.add(u)
            db.session.commit()

            default_dishes = Dish.query.filter_by(is_default=True).all()
            for d in default_dishes:
                if u.vegetarian and not d.vegetarian:
                    continue
                db.session.add(UserDishWeight(user_id=u.id, dish_id=d.id, weight=1.0))
            db.session.commit()
            break
    else:
        print(f"Did not find user: {first_name} {last_name}")

addRestaurant('Oishi', [('Ricebowl: Red Curry Tofu + Misosuppe', True), ('Bento: Crispy Chicken + Misosuppe', False)], weight=2.0)
addRestaurant('Bio Frische', [('Dal Makhni', True), ('Butter Chicken', False)])
addRestaurant('Fladerei', [('Tagesfladen (veg.)', True)], active=False)
addRestaurant('Pasta Day', [('Unlimited Pasta', True)], active=False)
addRestaurant('Sägewerk', [('Pizza Margharita', True)], weight=0.5)
addRestaurant('Pizzeria Riva', [('Pizza Margharita', True)], weight=0.5)

addUser('Michael', 'Scherbela', False, True)
addUser('Leon', 'Gerard', False)
addUser('Pavol', 'Harar', True)
addUser('Julius', 'Berner', True)
addUser('Lukas', 'Liehr', False)

proposeRestaurantSchedule()
proposeOrdererSchedule()


