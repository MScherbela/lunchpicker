from app import db, app
import os
import json
from app import User, Restaurant, Dish, UserDishWeight
if os.path.isfile('/data/lunch.db'):
    os.remove('/data/lunch.db')

with app.app_context():
    db.create_all()
    def addRestaurant(name, default_dishes, weight=1.0, active=True):
        r = Restaurant(name=name, weight=weight, active=active)
        db.session.add(r)
        db.session.commit()
        for name, veg,price in default_dishes:
            d = Dish(name=name, restaurant_id=r.id, vegetarian=veg, is_default=True, price=price)
            db.session.add(d)
            db.session.commit()
    
    with open('members.json') as f:
        member_data = json.load(f)
    
    def addUser(first_name, last_name, vegetarian, active=False, is_bot=False):
        if is_bot:
            u = User(first_name=first_name, last_name=last_name, active=active, is_bot=is_bot)
            db.session.add(u)
            db.session.commit()
        else:
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
                        db.session.add(UserDishWeight(user_id=u.id, dish_id=d.id, weight=0.5))
                        db.session.commit()
                    break
            else:
                print(f"Did not find user: {first_name} {last_name}")
    
    addRestaurant('Oishi', [('Ricebowl: Red Curry Tofu + Misosuppe', True, 750),
                            ('Bento: Crispy Chicken + Misosuppe', False, 790),
                            ('Bento: Fastenspeise + Misosuppe', True, 790)], weight=2.0)
    addRestaurant('Bio Frische', [('Dal Makhni (medium spicy)', True, 1050), ('Butter Chicken (medium spicy)', False, 1050), ('Chicken Korma (medium spicy)', False, 1050)])
    addRestaurant('Fladerei', [('Tagesfladen (veg.)', True, 710)], active=False)
    addRestaurant('Pasta Day', [('Unlimited Pasta', True, 300)], active=True)
    addRestaurant('Sägewerk', [('Large Pizza: Champignons + Paprika + Artischocken + Ruccola', True, 990)], active=False, weight=0.5)
    addRestaurant('Pizzeria Riva', [('Pizza Margharita', True, 890)], weight=0.5)
    
    addUser('Michael', 'Scherbela', False, True)
    addUser('Leon', 'Gerard', False, True)
    addUser('Pavol', 'Harar', True, True)
    addUser('Julius', 'Berner', True, True)
    addUser('Lukas', 'Liehr', False, True)
    addUser('Martin', 'Rathmair', True, True)
    addUser('Pasta Bot', '', False, True, True)


