from app import db
import os
import json
from app import User, Restaurant, Dish, UserDishWeight, RestaurantChoice, DishChoice, OrdererChoice
from app import proposeOrdererSchedule, proposeRestaurantSchedule

proposeOrdererSchedule()
proposeRestaurantSchedule()

result = db.session.query(RestaurantChoice, OrdererChoice).outerjoin(OrdererChoice, OrdererChoice.date == RestaurantChoice.date).all()
print(result)


