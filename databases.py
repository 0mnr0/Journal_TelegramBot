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
        return

    new_notification = {
        "uid": uid,
        "time": time,
        "additionalDay": day,
        "is_silent": is_silent,
        "created_at": datetime.now()
    }

    collection.insert_one(new_notification)


def clear_user_notify_list(uid):
    collection.delete_many({"uid": uid})


def get_users_by_notification_time(time):
    notifications = collection.find({"time": time})

    if notifications.collection.count_documents({"time": time}) == 0:
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



#Create if not exsts
mongoStat = client['EggHunters']
if not mongoStat.list_collection_names():
    mongoStat.create_collection("EasterEggDay")

EasterCollection = mongoStat['EasterEggDay']
class MStats:
    def __init__(self):
        pass

    @staticmethod
    def get_stats(userId, ticklish):
        return EasterCollection.find_one({"uid": userId, "ticklished": ticklish})

    @staticmethod
    def save_stats(userId, ticklish, user_name):
        if Stats.get_stats(userId, ticklish) is None:
            EasterCollection.insert_one({"uid": userId, "ticklished": ticklish, "name": user_name, "count": 1})
        else:
            EasterCollection.update_one({"uid": userId}, {"$inc": {"count": 1}})


Stats = MStats()




if "DayListener" not in db.list_collection_names():
    db.create_collection("DayListener")

dayListenBase = db["DayListener"]

class DayListener:
    @staticmethod
    def AddDayListener(chatId, day):
        if not DayListener.isChatExists(chatId):
            dayListenBase.insert_one({"chatId": chatId, "days": [day]})
        else:
            dayListenBase.update_one({"chatId": chatId}, {"$push": {"days": day}})
        
    
    @staticmethod
    def GetDayListenerList(chatId):
        if not DayListener.isChatExists(chatId):
            return []

        retValue = dayListenBase.find_one({"chatId": chatId})
        if retValue is None:
            return []
        retValue = retValue.get("days")
        return [] if retValue is None else retValue
    
    @staticmethod
    def isChatExists(chatId):
        return dayListenBase.find_one({"chatId": chatId}) is not None

    @staticmethod
    def RemoveDayListener(chatId, day):
        dayListenBase.update_one({"chatId": chatId}, {"$pull": {"days": day}})
        
        
    @staticmethod
    def GetListenersCount(chatId):
        if not DayListener.isChatExists(chatId):
            return 0
        retValue = dayListenBase.find_one({"chatId": chatId})
        if retValue is None:
            return 0
        retValue = retValue.get("days")
        return 0 if retValue is None else len(retValue)

    @staticmethod
    def IsDayExists(chatId, day):
        if not DayListener.isChatExists(chatId):
            return False
        return day in DayListener.GetDayListenerList(chatId)

    @staticmethod
    def GetListByChatId(chatId):
        if not DayListener.isChatExists(chatId):
            return []
        return dayListenBase.find_one({"chatId": chatId})


    @staticmethod
    def GetChatIDList():
        return dayListenBase.distinct("chatId")
    
    @staticmethod
    def GetThreadID(chatId):
        if not DayListener.isChatExists(chatId):
            return False
        return dayListenBase.find_one({"chatId": chatId}).get("threadId")

    @staticmethod
    def SetThreadID(chatId, threadId):
        if not DayListener.isChatExists(chatId):
            return False
        dayListenBase.update_one({"chatId": chatId}, {"$set": {"threadId": threadId}})
        return None
