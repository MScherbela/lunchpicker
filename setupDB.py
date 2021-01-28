from app import db
import os
from datetime import date
os.remove('lunch.db')
db.create_all()
from app import User, Restaurant, Dish, DishChoice, RestaurantChoice

michael = User(first_name="Michael", last_name="Scherbela", slack_id="U01BM5PTL3G")
pavol = User(first_name="Pavol", last_name="Harar", slack_id="")
leon = User(first_name="Leon", last_name="Gerard", slack_id="")

oishi = Restaurant(name="Oishi")
biofrische = Restaurant(name="Bio Frische")
fladerei = Restaurant(name="Fladerei")

for x in [michael, pavol, leon, oishi, biofrische, fladerei]:
    db.session.add(x)
db.session.commit()

for d in ['Chicken Korma', 'Samosas']:
    db.session.add(Dish(name=d, restaurant_id=biofrische.id))
for d in ['Red Curry Tofu', 'Red Curry Chicken', 'Bento Bulgogi']:
    db.session.add(Dish(name=d, restaurant_id=oishi.id))
db.session.commit()


db.session.add(DishChoice(user_id=michael.id, dish_id=Dish.query.first().id, date=date.today()))
db.session.add(RestaurantChoice(restaurant_id=biofrische.id, date=date.today()))
db.session.commit()

print(DishChoice.query.filter_by(date=date.today()).all())

