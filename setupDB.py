from app import db
import os
os.remove('lunch.db')
db.create_all()
from app import User, Restaurant, Dish, DishChoice

michael = User(first_name="Michael", last_name="Scherbela")
pavol = User(first_name="Pavol", last_name="Harar")
leon = User(first_name="Leon", last_name="Gerard")

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

print(db.session.query(User).filter_by(first_name='Michael').first())

