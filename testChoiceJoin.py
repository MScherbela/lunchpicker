from app import db
import os
import json
from app import User, Restaurant, Dish, UserDishWeight, RestaurantChoice, DishChoice, OrdererChoice
from app import proposeOrdererSchedule, proposeRestaurantSchedule

proposeOrdererSchedule()
proposeRestaurantSchedule()

result = db.session.query(RestaurantChoice, OrdererChoice).outerjoin(OrdererChoice, OrdererChoice.date == RestaurantChoice.date).order_by(RestaurantChoice.date).all()
print(result)

for r in result:
    print(str(r[0]) + " "*10 + str(r[1]))


