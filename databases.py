from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017/")
db = client['notifications_db']
collection = db['notifications']


def add_user_to_notify_list(uid, time, day=None, is_silent=False):

    existing_entry = collection.find_one({
        "uid": uid,
        "time": time,
        "additionalDay": day
    })

    if existing_entry:
        print(f"Уведомление для пользователя {uid} на {time} уже существует.")
        return

    new_notification = {
        "uid": uid,
        "time": time,
        "additionalDay": day,
        "is_silent": is_silent,
        "created_at": datetime.now()
    }

    collection.insert_one(new_notification)
    print(f"Уведомление для пользователя {uid} добавлено.")


def clear_user_notify_list(uid):
    collection.delete_many({"uid": uid})


def get_users_by_notification_time(time):
    notifications = collection.find({"time": time})

    if notifications.collection.count_documents({"time": time}) == 0:
        print(f"Нет уведомлений для времени {time}.")
        return []

    # Выводим данные о пользователях
    users = []
    for notif in notifications:
        user_data = {
            "uid": notif.get("uid"),
            "additionalDay": notif.get("additionalDay"),
            "is_silent": notif.get("is_silent"),
            "created_at": notif.get("created_at"),
        }
        users.append(user_data)

    return users

def get_count_users_in_time(time):
    return collection.find({"time": time}).collection.count_documents({"time": time})

