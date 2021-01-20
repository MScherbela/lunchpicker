from app import db
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

db.session.add(Dish(name='Chicken Korma', restaurant_id=biofrische.id, user_id=michael.id))
db.session.add(Dish(name='Bento Crispy Chicken (mit Minifrühlingsrollen)', restaurant_id=oishi.id, user_id=michael.id))
db.session.add(Dish(name='Red Curry Tofu', restaurant_id=oishi.id, user_id=pavol.id))
db.session.add(Dish(name='Red Curry Chicken', restaurant_id=oishi.id, user_id=leon.id))
db.session.commit()

