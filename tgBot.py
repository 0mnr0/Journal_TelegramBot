import json
import math
import os
import random
import shutil
import time
from threading import *

import requests
import telebot
import telegramify_markdown  # 0.4.2 Supported only
from telebot import types
from telebot.types import ReactionTypeEmoji, InlineKeyboardButton, InlineKeyboardMarkup

from ai import *
from databases import *
from dateProcessor import *
from weather import *
import ContextDetection


ALLOWED_USER_ON_MAINTAINCE = 1903263685
IsMaintaince = False

#Version 1.1
days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

if not os.path.exists('EasterEggDayShown'):
    os.mkdir("EasterEggDayShown")

AdaptiveSchedule = db['AdaptiveSchedule']
class DBMessages: # MongoDB
    @staticmethod
    def RegisterMessageReloader(chatId, messageId, connectedFrom, gmtCorrection=0):
        AdaptiveSchedule.update_one({'chatId': chatId}, {'$set': {'messageId': messageId, 'gmtCorrection': gmtCorrection, 'connectedFrom': connectedFrom }}, upsert=True)

    @staticmethod
    def UnRegisterMessageReloader(chatId):
        AdaptiveSchedule.delete_one({'chatId': chatId})

    @staticmethod
    def GetAllMessagesById(chatId):
        return AdaptiveSchedule.find({'chatId': chatId})

    @staticmethod
    def GetAllMessages():
        return AdaptiveSchedule.find()

    @staticmethod
    def ChangeGMT(connectedFrom, gmtValue):
        #Can Be Not One Only
        AdaptiveSchedule.update_many({'connectedFrom': connectedFrom}, {'$set': {'gmtCorrection': gmtValue}})



def get(url, authToken=None):
    authToken = str(authToken)
    headers = {
        'origin': 'https://journal.top-academy.ru',
        'Referer': 'https://journal.top-academy.ru',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Authorization': 'Bearer ' + authToken
    }
    return requests.get(url, headers=headers)



def post(url, js, authToken='null'):
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'https://journal.top-academy.ru',
        'Referer': 'https://journal.top-academy.ru',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Authorization': 'Bearer ' + authToken
    }
    js = dictToJson(js)
    return requests.post(url, js, headers=headers)

def isForum(message):
    forum = message.json['chat'].get("is_forum")
    if forum and message.message_thread_id is not None:
        forum = message.message_thread_id
    return forum


userFolderPath = 'userInfo'

API_TOKEN = open('tkn.ini', 'r').read()
bot = telebot.TeleBot(API_TOKEN)


moscowTime = datetime.now()

def reInitTime():
    global moscowTime
    moscowTime = datetime.now()


def CreateFolderIfNotExists(path):
    if os.path.exists(path) != True:
        os.mkdir(path)


CreateFolderIfNotExists(userFolderPath)
CreateFolderIfNotExists(userFolderPath+'/notifyList')

def IsUserExists(userId):
    userId = str(userId)
    return os.path.exists(userFolderPath + '/' + userId)

def ReadBotJson(userId):
    if IsUserExists(userId):
        userId = str(userId)
        pathToJson = userFolderPath + '/' + userId + '/botInfo.json'
        file = open(pathToJson, 'r', encoding='utf-8')
        return json.loads(file.read())
    else:
        return None


def GetUserCity(userId):
    if IsUserExists(userId):
        userId = str(userId)
        pathToJson = userFolderPath + '/' + userId + '/botInfo.json'
        file = open(pathToJson, 'r', encoding='utf-8')
        return json.loads(file.read()).get("cityName")
    else:
        return None


def ReadJSON(pathToJson):
    pathToJson = userFolderPath + '/' + pathToJson
    file = open(pathToJson, 'r', encoding='utf-8')
    return json.loads(file.read())


def SaveJSON(pathToJson, savingJSON):
    pathToJson = userFolderPath + '/' + pathToJson
    with open(pathToJson, 'w', encoding='utf-8') as f:
        json.dump(savingJSON, f, ensure_ascii=False, indent=4)

def CreateFile(pathToFile, text=None):
    pathToFile = userFolderPath + '/' + pathToFile
    with open(pathToFile, 'w', encoding='utf-8') as f:
        if text is not None:
            f.write(text)

def SaveFile(pathToFile, text):
    pathToFile = userFolderPath + '/' + pathToFile
    with open(pathToFile, 'w', encoding='utf-8') as f:
        f.write(text)

def isGroupChat(message):
    return message.chat.type != "private"

def SaveFileByList(pathToFile, list):
    pathToFile = userFolderPath + '/' + pathToFile
    with open(pathToFile, 'w', encoding='utf-8') as f:
        for item in list:
            if item != '':
                #If last line then no append \n
                if item == list[-1]:
                    f.write(item)
                else:
                    f.write(item + '\n')

def ReadFile(pathToFile):
    pathToFile = userFolderPath + '/' + pathToFile
    with open(pathToFile, 'r', encoding='utf-8') as f:
        return f.read()

def AppendToFile(pathToFile, text):
    pathToFile = userFolderPath + '/' + pathToFile
    with open(pathToFile, 'a', encoding='utf-8') as f:
        f.write(text)

def IsUserRegistered(userId):
    if IsUserExists(userId):
        userId = str(userId)
        reg = ReadBotJson(userId)

        rs = reg.get('login') is not None and reg.get('password') is not None
        return rs
    else:
        return False

def SetWaitForLoginData(userId, state):
    userId = str(userId)
    reg = ReadBotJson(userId)
    reg['WaitForAuth'] = state
    SaveJSON(userId + '/botInfo.json', reg)

def SetWaitForNotify(userId, state):
    userId = str(userId)
    reg = ReadBotJson(userId)
    reg['notifySetup'] = state
    SaveJSON(userId + '/botInfo.json', reg)

def dictToJson(d):
    return json.dumps(d)

def isMessageFromGroup(msg):
    return msg.chat.type != 'private'

def isUserBanned(userId):
    if IsUserExists(userId):
        userId = str(userId)
        reg = ReadBotJson(userId)
        return reg.get('banned')
    else:
        return False


def RefreshAdaptiveMessage():
    ChangesThisTime = False
    while True:
        time.sleep(15)
        #Get Minute Of Current Time
        minute = (datetime.now().minute % 30) == 0
        if minute and not ChangesThisTime:
            ChangesThisTime = True
            WhatToRefresh = DBMessages.GetAllMessages()
            for message in WhatToRefresh:
                ChatID = message.get('chatId')
                uid = message.get('messageId')
                LinkedPerson = message.get('connectedFrom')
                NewShedTimeText = GetShedForTime(day=None, uid=str(LinkedPerson), NeedReAuth=True, tomorrow = False, secondsClarify=True)
                try:
                    bot.edit_message_text(chat_id=ChatID, message_id=uid, text=NewShedTimeText, parse_mode="MarkdownV2", reply_markup=get_keyboard())
                except Exception as e:
                    print(e)



AdaptiveChanges = Thread(target=RefreshAdaptiveMessage)
AdaptiveChanges.start()











def cleanNotifyList(uid):
    for time in os.listdir(userFolderPath+'/notifyList/'):
        for userId in os.listdir(userFolderPath+'/notifyList/'+time):
            if userId == uid:
                os.rmdir(userFolderPath+'/notifyList/'+time+'/'+userId)
                send_message(uid, "*Notifier*: \nПостоянные уведомления отключены", disable_notification=True)



lastTimeSended = None
alreadyNotified = []
maxLengthOfUsers = 0
def backgroundSend():
    global lastTimeSended
    while True:
        try:
            global alreadyNotified
            reInitTime()
            mscTime = moscowTime.strftime("%H:%M")
            maxLengthOfUsers = get_count_users_in_time(mscTime)

            usersToNotify = get_users_by_notification_time(mscTime)

            if lastTimeSended != mscTime or maxLengthOfUsers > len(alreadyNotified):
                if lastTimeSended != mscTime:
                    alreadyNotified = []
                lastTimeSended = mscTime


                if len(usersToNotify) > 0:
                    for userData in usersToNotify:
                        if userData.get('uid') in alreadyNotified:
                            continue

                        uid = userData.get('uid')
                        userDayMovement = userData.get('additionalDay')
                        userDaySilent = userData.get('is_silent')
                        tkn = EaseAuth(uid)
                        notifyForUser = Thread(target=sheduleNotifySender, args=(uid, tkn, userDayMovement, userDaySilent))
                        notifyForUser.start()
                        alreadyNotified.append(uid)

        except Exception as e:
            raise e

        time.sleep(5)
        try:
            backgroundSend()
        except:
            backgroundSend()


notifier = Thread(target=backgroundSend)
notifier.start()

def EaseAuth(uid):
    if IsUserRegistered(uid):
        authData = {
            "application_key": '6a56a5df2667e65aab73ce76d1dd737f7d1faef9c52e8b8c55ac75f565d8e8a6',
            "username": ReadBotJson(uid).get('login'),
            "password": ReadBotJson(uid).get('password'),
        }
        auth = post('https://msapi.top-academy.ru/api/v2/auth/login', authData)
        if auth.status_code == 200:
            responseJson = auth.json()
            tkn = responseJson.get('access_token')
            userInfo = ReadJSON(uid + '/botInfo.json')
            userInfo['jwtToken'] = tkn
            userInfo['jwtExpiries'] = responseJson.get('expires_in_access')
            SaveJSON(uid + '/botInfo.json', userInfo)
            return tkn
        else:
            return False
    else:
        return None

def DateNotifier():
    def CheckForChat(chatId):
        daysToCheck = DayListener.GetDayListenerList(chatId)
        for day in daysToCheck:
            if day < datetime.now() + timedelta(days=1):
                DayListener.RemoveDayListener(chatId, day)

            else:
                try:
                    basicUrl = 'https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter='+(day.strftime("%Y-%m-%d"))
                    value = get(basicUrl, EaseAuth(chatId))
                    if value.status_code == 200:
                        jsonResult = value.json()
                        if len(jsonResult) == 0:
                            continue

                        finalText = "Произошли изменения на дату " + day.strftime("%d.%m.%Y") + ":\n\n"
                        for lesson in jsonResult:
                            finalText += '>Пара ' + str(lesson.get('lesson')) + ':  ' + lesson.get('teacher_name') + '\n'
                            finalText += '```\n' + lesson.get('subject_name') + "\n"
                            finalText += lesson.get('started_at') + " - " + lesson.get('finished_at') + " (" + lesson.get(
                                'room_name') + ")\n"
                            finalText += "```\n"

                        bot.send_message(chatId, text=telegramify_markdown.markdownify(finalText), parse_mode='MarkdownV2')
                        DayListener.RemoveDayListener(chatId, day)
                except Exception as e:
                    bot.send_message(ALLOWED_USER_ON_MAINTAINCE, text=str(e), parse_mode='MarkdownV2')

    ChatIDS = DayListener.GetChatIDList()
    for chatId in ChatIDS:
        CheckForChat(chatId)
        time.sleep(1)

def backgroundDateNotify():
    while True:
        try:
            DateNotifier()
        except Exception as e:
            raise e

        time.sleep(60 * 60)

bgDateNotify = Thread(target=backgroundDateNotify)
bgDateNotify.start()



def UserRegister(userId, msgType):
    userId = str(userId)
    UserAuthed = False
    if os.path.exists(userFolderPath + '/' + userId + '/botInfo.json') == False:
        userFolder = userFolderPath + '/' + userId
        CreateFolderIfNotExists(userFolder)
        UserInfo = {
            'banned': False,
            'login': None,
            'password': None,
            'WaitForAuth': False,
            'chat_type': msgType,
            'jwtExpiries': 0,
            'jwtToken': None
        }
        SaveJSON(userId + '/botInfo.json', UserInfo)
        UserAuthed = IsUserRegistered(userId)
    return UserAuthed



# Handle '/start' and '/help'
@bot.message_handler(commands=['start'])
def send_welcome(message):
    forum = isForum(message)

    if not UserRegister(message.chat.id, message.chat.type):
        keyboard = types.InlineKeyboardMarkup()

        if not isMessageFromGroup(message):
            auth_button = types.InlineKeyboardButton(text="Авторизоваться", callback_data=f"auth:{message.chat.id}")
            keyboard.add(auth_button)
            bot.send_message(message.chat.id,
                text="Привет! Этот бот показывает расписание для вашего аккунта в Journal. Для этого нужна авторизация вашего аккунта в боте.",
                reply_markup=keyboard, message_thread_id=forum, disable_notification=True)
        else:


            additionalText = '\n\nID Группы: `'+str(message.chat.id)+'`.\nЗапомните ID выше и нажмите кнопку ниже, чтобы авторизовать бота в группе через личные сообщения (Обычная авторизация в группе недоступна из-за соображений безопасности).'
            send_message(message.chat.id,
                         "Привет! Этот бот показывает расписание для вашего аккунта в Journal. Для этого нужна авторизация вашего аккунта в боте. " + additionalText, message_thread_id=forum, disable_notification=True)

            keyboard = types.InlineKeyboardMarkup()
            auth_button = types.InlineKeyboardButton(text="Авторизовать группу", callback_data=f"groupAuth:{message.chat.id}")
            keyboard.add(auth_button)
            send_message(message.chat.id, "*Для нормальной работы бота выдайте ему роль администраотра*\n*Для того чтобы кнопка работала напишите ему в личные сообщения*\n\nАвторизация не доступна в группе. Используйте кнопку ниже для привязки аккаунту к группе:", reply_markup=keyboard, message_thread_id=forum, disable_notification=True)


# Функция для проверки прав администратора
def is_admin(chat_id):
    member = bot.get_chat_member(chat_id, bot.get_me().id)
    return member.status in ['administrator', 'creator']

@bot.message_handler(commands=['clearauth'])
def clearAuth(message):
    forum = isForum(message)

    uid = str(message.chat.id)
    if os.path.exists(userFolderPath + '/' + uid):
        shutil.rmtree(userFolderPath+'/'+uid)
        if isMessageFromGroup(message):
            send_message(uid, "Авторизация очищена. Чтобы привязать данные авторизации используйте /auth", message_thread_id=forum, disable_notification=True)
        else:
            send_message(uid, "Авторизация очищена. Чтобы привязать данные авторизации используйте /auth", message_thread_id=forum)


@bot.message_handler(commands=['cancelauth'])
def cancelauth(message):
    forum = isForum(message)

    uid = str(message.chat.id)
    UserInfo = ReadBotJson(uid)
    if UserInfo is not None:
        UserInfo['WaitForAuth'] = False
        SaveJSON(uid + '/botInfo.json', UserInfo)
        send_message(uid, "Авторизация отменена. Чтобы привязать данные авторизации используйте /auth", message_thread_id=forum)


@bot.message_handler(commands=['ImTeacher', 'imteacher'])
def ImTeacher(message):
    uid = str(message.chat.id)
    textInMsg = message.text.split(' ', 1)
    if len(textInMsg) == 1:
        bot.reply_to(message, text="Синтаксис команды: /ImTeacher {useOmni: <bool>}")
        return

    Command = textInMsg[1]


    botInfo = ReadJSON(uid + '/botInfo.json')
    try:
        Command = json.loads(Command)
    except Exception as e:
        print(e)
        bot.reply_to(message, text="Неправильный JSON во второй части сообщения")
        return



    botInfo['UseOmni'] = Command.get("useOmni")
    botInfo['TeacherCities'] = Command.get("cities")
    SaveJSON(uid + '/botInfo.json', botInfo)
    if Command.get("useOmni"):
        send_message(uid, "Учли! Теперь бот будет использовать *Omni* для поиска расписания")
    else:
        send_message(uid, "Учли! Теперь бот будет использовать *Journal* для поиска расписания")




@bot.message_handler(commands=['auth'])
def makeAuth(message, messageIsAnId=False):



    if messageIsAnId==False and isMessageFromGroup(message):
        if isUserBanned(message):
            send_message(message.chat.id, "\{ banned: true \}")
            return

        if not IsUserRegistered(message.chat.id):
            send_welcome(message)
            return
        else:
            send_message(message.chat.id, "Группа уже имеет данные авторизации. Вы можете авторизоваться заново используя /clearauth а затем /auth.")
            return


    user = message
    if type(message) is int:
        user = message

    if not IsUserExists(user):
        send_welcome(user)
        return

    if isUserBanned(user):
        send_message(user, "\{ banned: true \}")
        return

    SetWaitForLoginData(user, True)
    SetWaitForNotify(user, False)

    send_message(user, """
Начнём авторизацию. Чтобы авторизоваться в сервисе нужно указать логин, поставить запятую и указать пароль.\nПример:```MyLogin_ab01,Password12345!```\n\n
Если по каким-то причинам вы не можете авторизоваться через бота выполните команду /auth через какое-то время.
С текущего момента все сообщения которые вы пришлёте будут считаться как данные авторизации до тех пор пока вы не пришлёте корректные данные авторизации или не выполните комманду /cancelauth (отмена ожидания авторизации)
        """, disable_notification=True)
    ui = ReadBotJson(user)
    ui['WaitForAuth'] = True
    SaveJSON(user + '/botInfo.json', ui)


@bot.callback_query_handler(func=lambda call: call.data.startswith("auth"))
def auth_callback(call):
    bot.answer_callback_query(call.id)
    data = call.data.split(":")
    chat_id = data[1]
    makeAuth(chat_id, True)


def GetUseTextContext(uid):
    botInfo = ReadBotJson(uid)
    if botInfo.get("UseTextConfig") is None:
        return False
    else:
        return botInfo.get("UseTextConfig")


def SaveUseTextContext(uid, value):
    botInfo = ReadBotJson(uid)
    botInfo["UseTextConfig"] = value
    SaveJSON(str(uid) + '/botInfo.json', botInfo)

@bot.message_handler(commands=["chatContext", "chatcontext"])
def send_toggle_button(message):
    config = GetUseTextContext(message.chat.id)
    markup = telebot.types.InlineKeyboardMarkup()
    btn_text = f'Включить / отключить'
    markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data="toggleTextContext"))
    yesAwnser = "*Да*\n\nБот будет присылать расписание даже без команды.\nНапример: какие сегодня *пары*?"
    noAwnser = "*Нет*\n\nБот не покажет расписание без команды.\nПример: какие сегодня *пары*? - не сработает\nПример: какие сегодня *!пары*? - сработает"
    bot.send_message(message.chat.id, telegramify_markdown.markdownify(f'Использовать текст в сообщении для активации бота: {yesAwnser if config == True else noAwnser}'), reply_markup=markup, parse_mode="MarkdownV2", disable_notification=True)


@bot.callback_query_handler(func=lambda call: call.data == "toggleTextContext")
def toggle_config(call):
    uid = call.message.chat.id
    current_value = GetUseTextContext(uid)
    new_value = not current_value

    SaveUseTextContext(uid, new_value)

    btn_text = "Включить / отключить"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data="toggleTextContext"))

    yesAwnser = "*Да*\n\nБот будет присылать расписание даже без команды.\nНапример: какие сегодня *пары*?"
    noAwnser = "*Нет*\n\nБот не покажет расписание без команды.\nПример: какие сегодня *пары*? - не сработает\nПример: какие сегодня *!пары*? - сработает"
    new_text = f'Использовать текст в сообщении для активации бота: {yesAwnser if new_value == True else noAwnser}'

    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=telegramify_markdown.markdownify(new_text),
                          reply_markup=markup,
                          parse_mode="MarkdownV2")


@bot.callback_query_handler(func=lambda call: call.data.startswith("groupAuth"))
def groupauth_callback(call):
    bot.answer_callback_query(call.id)
    data = call.data.split(":")
    whoClicked = str(call.from_user.id)
    if IsUserExists(whoClicked) and not isUserBanned(whoClicked):
        if IsUserRegistered(whoClicked):
            if not IsUserRegistered(data[1]):
                SetWaitForLoginData(whoClicked, False)
                keyboard = types.InlineKeyboardMarkup()
                yesButton = types.InlineKeyboardButton(text="Да", callback_data=f"stateGroupAuth:True:"+data[1])
                noButton = types.InlineKeyboardButton(text="Отмена", callback_data=f"stateGroupAuth:False:"+data[1])
                if not isUserBanned(whoClicked):
                    keyboard.add(yesButton)
                    keyboard.add(noButton)
                send_message(whoClicked, "Подтвердите, что вы хотите авторизоваться в группе \nID: `" + (str(data[1])) + '`\n\n Нажимая кнопку "Да" вы соглашаетесь с тем что ваши данные Journal будут использованы для группы.',reply_markup=keyboard)
            else:
                send_message(whoClicked, "Вы не можете авторизовать группу так как она уже кем то авторизована. Напищите в группе комманду `/clearauth` для привязки ваших данных к группе")
        else:
            send_message(whoClicked, "Ваши данные не зарегистрированы. Пожалуйста, сперва сначала пройдите процесс авторизации /auth")
    else:
        try:
            if not isUserBanned(whoClicked):
                send_message(whoClicked, "Чтобы авторизоваться в группе, необходимо зарегистрироваться ваш Telegram аккаунт в боте.\n\nДля этого нужно использовать комманду /auth")
        except:
            pass


@bot.message_handler(commands=['help', 'помощь'])
def printHelp(message):
    finalText = """
    Список комманд: 
    
*/start* - Начтаь общение с ботом
*/auth* - Запуск процесса авторизации
*/cancelauth* - Отмена ожидания авторизации
*/clearauth* - Очистка данных авторизации
*/help*, */помощь* - Список комманд
*/cleanauthingroups* - Очистить авторизации групп поочерёдно
*/cleanauthbyid* - Очистка авторизации группы по её ID
*/passnotify* - Убрать отправку расписания
*/exams* - Показать экзамены
*/ai*, */помощьбедолагам* - Спросить ИИ (Использование - /ai <вопрос>)
*/notifyme* - Настроить ежедневную отправку расписания в формате часы:минуты
*/chatContext* - Указать, нужно ли боту отправлять расписание когда было упомянуто слово "пары" без команды
*/gmt* - Настройка сдвига времени для пользователя и для привязанных чатов
*/whatTimeForBot* - Узнать время которое сейчас видит бот

----
*/sched*, */shed*, */пары*, */расписание*, *!пары* - Показать расписание 

*Поддерживает параметры*
/shed <завтра, послезавтра, вчера, 2024-01-01, сегодня, +X, -X >
Значение по умолчанию: сегодня    

Команды: *!пары* и *!расписание* можно использовать в контексте. Пример:
*Какие завтра !пары*
----

Помощь по подключению бота для групп:
Подключите бота к группе, выдайте ему права администратора для отправки сообщений в чат (по умолчанию бот не может это делать если он подключен к групповому  чату)
Авторизируйте свой аккаунт в личных сообщениях. В группе пропишите комманду /auth и бот отправит кнопку с ссылкой. Нажмите на эту кнопку и вам придёт запрос на подтверждение от бота, подтвердите привязку и бот в группе сообщит об успешной привязке аккаунта! 
"""
    finalText = finalText.replace("-", "\\-").replace(".", "\\.").replace("!", "\\!").replace("(", "\\(").replace(")", "\\)").replace("<", "\\<").replace(">", "\\>").replace("}", "\\}").replace("{", "\\{").replace("+", "\\+")
    bot.reply_to(message, finalText, parse_mode='MarkdownV2')







def ReAuthInSystem(message=None, uidNotMessage=None):
    uid = uidNotMessage
    if uidNotMessage is None:
        uid = str(message.chat.id)

    if IsUserRegistered(uid):
        authData = {
            "application_key": '6a56a5df2667e65aab73ce76d1dd737f7d1faef9c52e8b8c55ac75f565d8e8a6',
            "username": ReadBotJson(uid).get('login'),
            "password": ReadBotJson(uid).get('password'),
        }
        auth = post('https://msapi.top-academy.ru/api/v2/auth/login', authData)
        if auth.status_code == 200:
            responseJson = auth.json()
            tkn = responseJson.get('access_token')
            userInfo = ReadJSON(uid + '/botInfo.json')
            userInfo['jwtToken'] = tkn
            userInfo['jwtExpiries'] = responseJson.get('expires_in_access')
            if uidNotMessage is None and message.chat.type != 'private':
                userInfo['chat_type'] = message.chat.type
            SaveJSON(uid + '/botInfo.json', userInfo)
            return tkn
        else:
            return None
    else:
        bot.reply_to(message, "Для начала привяжите ваши данные в боте: /auth")
        return None

@bot.message_handler(commands=['exams'])
def exams(message):
    forum = isForum(message)

    if isUserBanned(message.chat.id):
        send_message(message.chat.id, "idk", message_thread_id=forum)
        return

    if IsUserRegistered(message.chat.id):
        userExams = get('https://msapi.top-academy.ru/api/v2/dashboard/info/future-exams', ReAuthInSystem(message))
        userExams = userExams.json()
        #[{'spec': 'Операционные системы и среды', 'date': '2024-12-13'}]

        finalResponse = "Расписание экзаменов:\n\n"

        if len(userExams) > 0:
            for exam in userExams:
                finalResponse += f">*{exam.get('date')}*:\n{exam.get('spec')}\n\n"
        else:
            finalResponse = "\n\n > Пусто"

        send_message(message.chat.id, finalResponse, message_thread_id=forum)

def getGmtCorrection(uid):
    try:
        botInfo = ReadBotJson(uid)
        if IsUserRegistered(uid):

            if botInfo.get('gmtCorrection') is None:
                return 0
            else:
                return botInfo.get('gmtCorrection')
        return 0
    except:
        return 0

@bot.message_handler(commands=['passnotify'])
def cancelNotify(message):
    uid = str(message.chat.id)
    clear_user_notify_list(uid)
    cleanNotifyList(uid)


@bot.message_handler(commands=['whatTimeForBot', 'whattimeforbot'])
def whatTimeForBot(message):
    uid = str(message.chat.id)
    bot.send_message(uid, str(moscowTime.strftime("%H_%M")))
    timeCorrected = moscowTime+timedelta(hours=getGmtCorrection(uid))
    bot.send_message(uid, str("With gmt correction: "+timeCorrected.strftime("%H_%M")))




@bot.message_handler(commands=['notifyme', 'notify'])
def notifier(message):
    uid = str(message.chat.id)

    send_message(uid, """
Вы настраиваете уведомления. Отправьте время в формате часы:минуты в формате МСК времени.\n\nПример сообщения: ```10:00``` или ```06.30```\n\n
Вы также можете дополнить сообщение если нужно получить расписание на следющий день, например: */notify 23:00 1*\n
Единица в команде указывает кол-во сдвигов по дням, то есть если указать 1 то бот пришлёт расписание на следующий день.\n
\nВы так-же можете дописать *silent* к вашей команде что заставит бота отправлять расписание "без звука" *Примеры*: ``` 23:00 1 silent```\n``` 10.00 silent``` 
""")
    SetWaitForNotify(uid, True)


def sheduleNotifySender(uid, lastJwt, additionalDay=0, silent=False):
    if IsUserRegistered(uid):
        if isUserBanned(uid):
            return


        basicUrl = 'https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter='
        date = datetime.today()
        try:
            additionalDay = int(additionalDay)
        except:
            additionalDay = 0

        date = date + timedelta(days=additionalDay)

        date=date.strftime('%Y-%m-%d')
        # https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter= YYYY - MM - DD

        fetchResult = get(basicUrl + date, lastJwt)
        if fetchResult.status_code == 200:
            jsonResult = fetchResult.json()

            finalText = ""
            for lesson in jsonResult:
                finalText += '>Пара ' + str(lesson.get('lesson')) + ':  ' + lesson.get('teacher_name') + '\n'
                finalText += '```\n' + lesson.get('subject_name') + "\n"
                finalText += lesson.get('started_at') + " - " + lesson.get('finished_at') + " (" + lesson.get('room_name') + ")\n"
                finalText += "```\n"

            if len(finalText) == 0:
                finalText = "В этот день ничего нет :)"

            converted = telegramify_markdown.markdownify(
                finalText,
                max_line_length=None,
                normalize_whitespace=False
            )
            silent = (silent==True)

            if silent:
                bot.send_message(uid, "*Silent Notifier Service*\nПары на `" + date + "`:\n\n" + converted, disable_notification=silent, parse_mode='MarkdownV2')
            else:
                bot.send_message(uid, "*Notifier Service*\nПары на `" + date + "`:\n\n" + converted, disable_notification=silent, parse_mode='MarkdownV2')



def GetShedForTime(day=None, uid=None, NeedReAuth = True, tomorrow=False, secondsClarify=False):
    if day is None:
        day = datetime.now()  # Берем текущую дату и время
    elif isinstance(day, str):
        day = datetime.strptime(day, "%Y-%m-%d")  # Конвертируем строку в datetime

    timeCorrection = getGmtCorrection(uid)  # Получаем корректировку времени
    day = day + timedelta(hours=timeCorrection)  # Добавляем часы

    if NeedReAuth and uid is not None:
        ReAuthInSystem(uidNotMessage=uid)

    uiInfo = ReadBotJson(uid)
    lastJwt = uiInfo.get('jwtToken')
    tomorrowText = "(Завтра)" if tomorrow else ""

    basicUrl = 'https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter='
    finalDay = day.strftime('%Y-%m-%d')
    fetchResult = get(basicUrl + finalDay, lastJwt)
    if fetchResult.status_code == 200:
        jsonResult = fetchResult.json()
        startText = f"> Бот покажет расписание на тот день, на который вы нажали\n\n"

        finalText = ""
        for lesson in jsonResult:
            finalText += '>*Пара ' + str(lesson.get('lesson')) + ':  ' + lesson.get('teacher_name') + '*\n'
            finalText += '```\n' + lesson.get('subject_name') + "\n"
            finalText += lesson.get('started_at') + " - " + lesson.get('finished_at') + " (" + lesson.get(
                'room_name') + ")\n"
            finalText += "```\n"

        if len(jsonResult) == 0:
            finalText = "\n>В этот день ничего нет :)"

        #finalText = f"UID: {uid}\nДень: `{finalDay}`\nПоследнее обновление: `{datetime.now().strftime('%H:%M')}`\n\n"+finalText
        finalText = f"{startText}\nПоследнее обновление: `{datetime.now().strftime('%H:%M:%S') if secondsClarify else datetime.now().strftime('%H:%M')}`\nДень: `{finalDay} {day.strftime('%H:%M')} {tomorrowText}`\n\n"+finalText

        return telegramify_markdown.markdownify(finalText)
    return telegramify_markdown.markdownify(f"Error: fetchResult.status_code != 200 ({fetchResult.status_code})")



DynamicMessagesActions = [
    "<-",
    "->",
    "Сегодня",
    "Завтра",
    "UpdateGlobally"
]

def get_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("Сегодня", callback_data="Сегодня")
    )
    keyboard.row(
        InlineKeyboardButton("Завтра", callback_data="Завтра")
    )
    keyboard.row(
        InlineKeyboardButton("⬅", callback_data="<-"),
        InlineKeyboardButton("Сейчас", callback_data="UpdateGlobally"),
        InlineKeyboardButton("➡", callback_data="->")
    )
    return keyboard

def IsUserAdmin(chat_id, user_id):
    member = bot.get_chat_member(chat_id, user_id)
    return member.status in ['administrator', 'creator']


@bot.message_handler(commands=['setcity'])
def setcity(message):
    uid = str(message.chat.id)
    forum = isForum(message)
    if forum and not IsUserAdmin(uid, message.from_user.id):
        bot.reply_to(message, "Эту комманду может выполнить только администратора группы!", message_thread_id=forum)
        return
    city = message.text.split(" ")
    if len(city) != 2:
        bot.reply_to(message, "Команда написана неправильно! Используйте /setcity Москва или /setcity Санкт-Петербург. Чтобы отключить погоду - используйте комманду /setcity off", message_thread_id=forum)
        return
    city = city[1]


    botin = ReadJSON(uid + '/botInfo.json')
    if city == "off" and botin.get("cityName") is not None:
        botin.pop("cityName")
    else:
        botin['cityName'] = city
    SaveJSON(uid+'/botInfo.json', botin)
    if city != "off":
        bot.reply_to(message, f"Вы указали город \"{city}\". Теперь погода будет показываться вместе с расписанием к привязанному городу. Отключить привязку к городу можно коммандой - /setcity off", message_thread_id=forum)
    else:
        bot.reply_to(message, "Вы отключили привязку к городу!", message_thread_id=forum)

@bot.message_handler(commands=['dynamicmessage', 'DynamicMessage'])
def DynamicMessage(message):
    uid = str(message.chat.id)
    userInitCmd = message.from_user.id

    if not IsUserRegistered(userInitCmd):
        bot.reply_to(message, "Обновление сообщения не будет учитывать сдвиг времени, для того чтобы учитывать - человек, привязавший группу должен выполнить эту команду заново", parse_mode='MarkdownV2')





    forum = isForum(message)
    botin = ReadJSON(uid + '/botInfo.json')
    DynamicChatID = botin.get('DynamicChatID')
    DynamicForumID = botin.get('DynamicForumID')
    DynamicChatMessage = botin.get('DynamicID')

    ShedForDay = GetShedForTime(uid=uid, NeedReAuth=True)




    if DynamicChatMessage is not None:
        try:
            bot.delete_message(DynamicChatID, DynamicChatMessage)
            DBMessages.UnRegisterMessageReloader(DynamicChatID)
        except: print("Failed to delete dynamic message")

    BotMessage = bot.send_message(uid, text=ShedForDay, message_thread_id=forum, reply_markup=get_keyboard(), parse_mode="MarkdownV2", disable_notification=True)
    DynamicChatMessage, botin['DynamicID'] = 2 * [BotMessage.message_id]
    DynamicChatID, botin['DynamicChatID'] = 2 * [uid]
    DynamicForumID, botin['DynamicForumID'] = 2 * [forum]
    SaveJSON(uid+'/botInfo.json', botin)
    DBMessages.RegisterMessageReloader(DynamicChatID, DynamicChatMessage, userInitCmd, getGmtCorrection(userInitCmd))

    try:
        bot.delete_message(uid, message.message_id)
    except:
        pass




@bot.callback_query_handler(func=lambda call: call.data in DynamicMessagesActions)
def callback_handler(call):
    current_text = call.message.text
    MessageUpdateTime = re.search(r"Последнее обновление: \s*(\S+)", current_text)
    if MessageUpdateTime is not None:
        MessageUpdateTime = MessageUpdateTime.group(1)
    else:
        MessageUpdateTime = datetime.now().strftime('%H:%M:%S')
    uid = call.message.chat.id
    bot.set_message_reaction(call.message.chat.id, call.message.id, [ReactionTypeEmoji('👀')], is_big=False)
    #uid = re.search(r"UID:\s*(\S+)", current_text).group(1)

    match = re.search(r"День: \s*(\d{4}-\d{2}-\d{2})", current_text)
    if match is not None:
        match = match.group(1)

    DayInMessage = match
    CurrentDayWithGMT = (datetime.now() + timedelta(hours=getGmtCorrection(uid))).strftime('%Y-%m-%d')
    uid = str(uid)
    if DayInMessage == CurrentDayWithGMT and call.data == "Сегодня":
        print("Обновление текущего дня из текущего дня пропущено")
        return
    if "(Завтра)" in current_text and call.data == "Завтра":
        print("Обновление завтрашнего дня с уже написанным завтрашним днём")
        return

    tomorrowBtn = False
    if match:
        match = datetime.strptime(match, "%Y-%m-%d")
        if call.data == "Сегодня":
            match = datetime.now().strftime("%Y-%m-%d")
        if call.data == "Завтра":
            match = datetime.today() + timedelta(days=1)
            tomorrowBtn = True
        if call.data == "->":
            match = match + timedelta(days=1)
        if call.data == "<-":
            match = match - timedelta(days=1)
        if call.data == "UpdateGlobally":
            match = None

        #Convert to datetime and get in %Y-%m-%d format


    GetCurrentTime = (datetime.today() + timedelta(hours=getGmtCorrection(uid))).strftime("%H:%M")
    NeedReAuth = False
    try:
        NeedReAuth = (datetime.strptime(GetCurrentTime, "%H:%M") - datetime.strptime(MessageUpdateTime, "%H:%M")).total_seconds() > 14400
    except:
        NeedReAuth = True
    NewShedTimeText = GetShedForTime(day=match, uid=uid, NeedReAuth=NeedReAuth, tomorrow = tomorrowBtn)


    bot.set_message_reaction(call.message.chat.id, call.message.id, [ReactionTypeEmoji('👨‍💻')], is_big=False)
    try:
        bot.edit_message_text(
            chat_id=uid,
            message_id=call.message.message_id,
            text=NewShedTimeText,  # Меняем текст на выбранный
            reply_markup=get_keyboard(),
            parse_mode="MarkdownV2"  # Оставляем кнопки
        )
        bot.set_message_reaction(call.message.chat.id, call.message.id, [ReactionTypeEmoji('😁')], is_big=False)
    except Exception as e:
        print(e)

    bot.answer_callback_query(call.id, show_alert=False)










def ClearCachedJWT(uid):
    if IsUserRegistered(uid):
        BotInfo = open('userInfo/' + uid + '/botInfo.json', 'r+', encoding='utf-8')
        userInfo = json.load(BotInfo)
        userInfo['jwtToken'] = None
        userInfo['jwtExpiries'] = None
        SaveJSON(uid + '/botInfo.json', userInfo)


def isFirstApril():
    return datetime.today().month == 4 and datetime.today().day == 1

def ThreePercentChance():
    return random.randint(1, 100) <= 3


@bot.message_handler(commands=['ai', 'помощьБедолагам', 'помощьбедолагам', 'ПомощьБедолагам', 'BastardHelp'])
def aihelp(message):
    try:
        prompt = " ".join(message.text.split(" ")[1::])
        bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji('🤔')], is_big=False)
        awnser = WalkingTowardsTheRiver.ThinkAbout(prompt)
        awnser = telegramify_markdown.markdownify(awnser)
        bot.reply_to(message, awnser, message_thread_id=isForum(message), parse_mode='MarkdownV2')
    except Exception as e:
        print(e)
        bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji('🤷')], is_big=False)


@bot.message_handler(commands=['gmt'])
def setupGmtCorrection(message):
    uid = str(message.chat.id)
    if IsUserRegistered(message.from_user.id):
        msg = message.text.split(' ')
        if len(msg) != 2:
            bot.reply_to(message, text=telegramify_markdown.markdownify("Для корректировки времени нужно выполнить комманду в формате:\n\n```/gmt +1```\nГде +1 - сдвиг на 1 час от GMT 0 (Например: Москва - GMT +3, Самара - GMT +4).\n\nЧтобы узнать текущее время для бота, напишите ему команду:\n```/whatTimeForBot```"), parse_mode='MarkdownV2', message_thread_id=isForum(message))
            return
        gmtCorrection = msg[1]
        gmtCorrection = gmtCorrection.replace('+', '')
        if not gmtCorrection.isdigit() and '-' not in gmtCorrection:
            bot.reply_to(message, text=telegramify_markdown.markdownify("Введенное значение должно быть числом! (Положительным, отрицательным или нулевым)"), parse_mode='MarkdownV2', message_thread_id=isForum(message))
            return
        gmtCorrection = int(gmtCorrection)
        botInfo = ReadBotJson(uid)
        botInfo['gmtCorrection'] = gmtCorrection
        if gmtCorrection == 0:
            botInfo['gmtCorrection'] = None
        SaveJSON(uid + '/botInfo.json', botInfo)

        try: DBMessages.ChangeGMT(connectedFrom=message.from_user.id, gmtValue=gmtCorrection)
        except Exception as e: print("Failed wrok with db:", e)

        bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji('👍')], is_big=False)
    else:
        bot.send_message(message.chat.id, text=telegramify_markdown.markdownify("Вы не зарегистрированы!"), parse_mode='MarkdownV2', message_thread_id=isForum(message))


def isEasterDay():
    return datetime.today().month == 4 and datetime.today().day == 20

def EasterEggDayShown(chat_id, rewrite=False):
    if not os.path.exists('EasterEggDayShown'):
        os.mkdir("EasterEggDayShown")

    if not rewrite:
        return os.path.exists('EasterEggDayShown/'+str(chat_id)+'.yes')
    else:
        pass
        #   open('EasterEggDayShown/'+str(chat_id)+'.yes', 'w').close()



@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    user_name = ""
    if poll_answer.user.first_name is not None:
        user_name += poll_answer.user.first_name
    if poll_answer.user.last_name is not None:
        user_name += " " + poll_answer.user.last_name

    selected_option_ids = poll_answer.option_ids
    Stats.save_stats(user_id, selected_option_ids[0] == 1, user_name)




@bot.message_handler(commands=['пары', 'расписание', 'sched', 'shed', 'Пары', 'ПАРЫ'])
def fetchDate(message, Relaunch=False, Sended=None):
    uid = str(message.chat.id)


    if uid != '1903263685':
        #bot.reply_to(message, text="Идут работы, спросите чуть позже", message_thread_id=isForum(message), parse_mode='MarkdownV2')
        #return
        pass



    if isEasterDay() and not EasterEggDayShown(message.chat.id):
        bot.send_poll(message.chat.id, 'Вы уже покрасили яички?', options=['Да','Нет, мне щекотно'], message_thread_id=isForum(message), is_anonymous=False)
        EasterEggDayShown(message.chat.id, rewrite=True)




    forum = isForum(message)

    try:
        if isGroupChat(message) and not is_admin(message.chat.id):
            bot.reply_to(message, text="Бот не может работать без прав администратора :(", message_thread_id=forum)

        if isFirstApril() and not Relaunch:
            with open("EasterEggs/shedule_in_4k.jpg", "rb") as photo:
                bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption="Вот расписание на указанный день!",
                    message_thread_id=forum,
                    reply_to_message_id=message.message_id  # Ответ на сообщение пользователя
                )
            time.sleep(7)
        else:
            if False:
                if ThreePercentChance():
                    with open("EasterEggs/walter_black.jpg", "rb") as photo:
                        bot.send_photo(
                            chat_id=message.chat.id,
                            photo=photo,
                            caption="Nuh, i dont want to do it",
                            message_thread_id=forum,
                            reply_to_message_id=message.message_id  # Ответ на сообщение пользователя
                        )
                    time.sleep(5)




        if IsUserRegistered(uid):

            if isUserBanned(message.from_user.id):
                return


            bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji('👀')], is_big=False)


            global showingText
            global operationDay
            sended_msg = Sended
            if not Relaunch:
                sended_msg = send_message(uid, "Секунду, ищем расписание...", disable_notification=True, message_thread_id=forum)

            uiInfo = ReadBotJson(uid)
            lastJwt = uiInfo.get('jwtToken')
            basicUrl = 'https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter='
            operationDay = datetime.today()
            showingText = "сегодня"

            newJwt = ReAuthInSystem(message)
            if type(newJwt) == str:
                lastJwt = newJwt

            if strClear(message.text).isdigit():
                try:
                    maybeItsADay = clearDate(message.text)
                    convertedDate = parse_date(maybeItsADay)
                    operationDay = convertedDate
                    showingText = convertedDate
                except Exception as e:
                    operationDay = datetime.today()
                    showingText = "сегодня"

            if isItPlusOperation(message.text):
                operation, dayNum = getTextOperation(message.text)
                if operation == "+":
                    operationDay = datetime.today() + timedelta(days=int(dayNum))
                    showingText = operationDay.strftime('%Y-%m-%d')
                elif operation == "-":
                    operationDay = datetime.today() - timedelta(days=int(dayNum))
                    showingText = operationDay.strftime('%Y-%m-%d')



            def correctDatetimeType(date_value):
                if isinstance(date_value, str):
                    return datetime.strptime(date_value, "%Y-%m-%d")
                return date_value

            operationDay = correctDatetimeType(operationDay)
            operationDay = operationDay + timedelta(hours=getGmtCorrection(uid))


            if IsDateTimeInMessage(message.text):
                operationDay = getDateByText(message.text, operationDay)
                showingText = operationDay.strftime('%Y-%m-%d')

            if "послезавтра" in message.text.lower():
                operationDay = operationDay+timedelta(days=2)
                showingText = f"послезавтра"
            elif "завтра" in message.text.lower() or "завтрв" in message.text.lower():
                operationDay = operationDay + timedelta(days=1)
                showingText = f"завтра"
            elif "вчера" in message.text.lower():
                operationDay = operationDay-timedelta(days=1)
                showingText = f"вчера"


            if type(operationDay) != str:
                operationDay = operationDay.strftime('%Y-%m-%d')

            date_object = datetime.strptime(operationDay, "%Y-%m-%d")
            day_of_week = days[date_object.weekday()]
            showingText += f" ({day_of_week})"


            if lastJwt is not None:
                # JWT Key Is Still Valid
                # Example of url by finding a day:
                # https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter= YYYY - MM - DD

                Tries = 1
                FixedByCycle = False
                operationDay = operationDay
                fetchResult = get(basicUrl+operationDay, lastJwt)



                if fetchResult.status_code != 200:
                    Tries += 1
                    for i in range(4):
                        fetchResult = get(basicUrl+operationDay, ReAuthInSystem(message))
                        if fetchResult.status_code == 200:
                            FixedByCycle = True
                            break
                        else:
                            time.sleep(0.3)


                if fetchResult.status_code == 200:
                    jsonResult = fetchResult.json()

                    finalText = ""


                    for lesson in jsonResult:
                        finalText += '>*Пара ' + str(lesson.get('lesson')) + ':  '+lesson.get('teacher_name')+'*\n'
                        finalText += '```\n' + lesson.get('subject_name') + "\n"
                        finalText += lesson.get('started_at')+" - "+lesson.get('finished_at')+" ("+lesson.get('room_name')+")\n"
                        finalText += "```\n"


                    if len(finalText) > 0 and FixedByCycle:
                        finalText += f"\n\n*Успешно выполнен патч исправления пустого расписания (LuckyTry: {str(Tries)} / 5)*"


                    if sended_msg is not None:
                        try:
                            bot.edit_message_text(chat_id=message.chat.id, message_id=sended_msg.message_id, text="Пары на *" + showingText + "*:\n\n" +finalText, parse_mode='MarkdownV2')
                            return
                        except: pass

                    if len(finalText) == 0:
                        finalText="В этот день ничего нет :D"


                    finalText = "Пары на *" + showingText + "*:\n\n" + finalText

                    converted = telegramify_markdown.markdownify(
                        finalText,
                        max_line_length=None,
                        normalize_whitespace=False
                    )
                    try:
                        bot.edit_message_text(chat_id=message.chat.id, message_id=sended_msg.message_id, text=converted, parse_mode='MarkdownV2')
                    except:
                        sended_msg = bot.send_message(message.chat.id, text=converted, parse_mode='MarkdownV2', message_thread_id=forum)


                    userExams = get('https://msapi.top-academy.ru/api/v2/dashboard/info/future-exams', lastJwt)
                    if fetchResult.status_code == 200:
                        userExams = userExams.json()
                    else:
                        userExams = []

                    ### Exams Check

                    examsText = ""
                    try:
                        if len(userExams) > 0:
                            ExamsToday = False
                            for exam in userExams:
                                if exam.get('date') == operationDay and not ExamsToday:
                                    examsText += "\n Экзамены:\n"
                                if exam.get('date') == operationDay:
                                    ExamsToday = True
                                    examsText += f">*\"{exam.get('spec')}\"*\n"


                        examText = telegramify_markdown.markdownify(
                            finalText+examsText,
                            max_line_length=None,
                            normalize_whitespace=False
                        )

                        try:
                            bot.edit_message_text(chat_id=message.chat.id, message_id=sended_msg.message_id, text=examText, parse_mode='MarkdownV2')
                        except Exception as e:
                            raise e

                    except Exception as e:
                        print(e)


                    UserCity = GetUserCity(message.from_user.id)
                    if UserCity != "off" and UserCity is not None:
                        weatherData = WeatherAPI.OnDay(GetUserCity(uid), operationDay)
                        weatherSymbols = ["☀️", "🌤️", "🌥️", "☁️"]
                        weatherText = "Погода: \n"
                        timenames = ["Утром", "Днём", "Вечером"]
                        timeCodes =  ["morning", "day", "evening"]
                        for i in range(len(timeCodes)):
                            timeName = timenames[i]
                            pickedTime = timeCodes[i]
                            if type(weatherData.get(pickedTime)) == float:
                                weatherText += f"{random.choice(weatherSymbols)} *{timeName}: {math.floor(weatherData.get(pickedTime))}° *\n"

                        try:
                            bot.edit_message_text(chat_id=message.chat.id, message_id=sended_msg.message_id, text=examText+weatherText, parse_mode='MarkdownV2')
                        except Exception as e:
                            raise e




                else:
                    if not Relaunch:
                        ClearCachedJWT(uid)
                        bot.delete_message(message_id=sended_msg.message_id, chat_id=message.chat.id)
                        fetchDate(message, True, sended_msg)
                    else:
                        send_message(message.chat.id, f"Не удалось загрузить расписание. Что-то с JWT ключом... (FetchAPI Result Code: {fetchResult.status_code})", message_thread_id=forum)
            else:
                if not Relaunch:
                    ClearCachedJWT(uid)
                    bot.delete_message(message_id=sended_msg.message_id, chat_id=message.chat.id)
                    fetchDate(message, True, sended_msg)
                else:
                    send_message(message.chat.id, "Не удалось загрузить расписание. Что-то с JWT ключом... (lastJwt is None)", message_thread_id=forum)
    except Exception as e:
        er = telegramify_markdown.markdownify(str(e), max_line_length=None, normalize_whitespace=False)
        bot.reply_to(message, er, parse_mode='MarkdownV2')
        raise e



@bot.message_handler(commands=['cleanauthingroups'])
def globalCleaner(message):
        uid = str(message.chat.id)
        if not isMessageFromGroup(message):
            if os.path.exists(userFolderPath + '/' + uid + '/list.inf'):
                userConnectedGroups = ReadFile(uid + '/list.inf').split("\n")
                for groupid in userConnectedGroups:
                    if os.path.exists(userFolderPath + '/' + groupid) and groupid != '':
                        try:
                            groupInt = int(groupid)
                            userConnectedGroups.remove(groupid)
                            SaveFileByList(uid + '/list.inf', userConnectedGroups)

                            groupBotData = ReadJSON(groupid + '/botInfo.json')
                            groupBotData['login'] = None
                            groupBotData['password'] = None
                            groupBotData['jwtToken'] = None
                            groupBotData['jwtExpiries'] = None
                            SaveJSON(groupid + '/botInfo.json', groupBotData)
                            send_message(uid, "Авторизация для группы *"+groupid+"* очищена. Групп с вашей авторизацией осталось: "+(str(len(userConnectedGroups))))
                            send_message(groupInt, """Авторизация для этой группы была отозвана. Используйте комманду /auth чтобы зарегистрировать этого бота.""")
                        except Exception as e:
                            send_message(uid, e)

            else:
                send_message(uid, "У вас нет ни одной привязанной группы!")
        else:
            bot.reply_to(message, "Вы не можете использовать эту комманду в группах!")




@bot.message_handler(commands=['daylistener'])
def dayListener(message):
    uid = str(message.chat.id)
    msgText = message.text.replace("/daylistener ", "").split()
    day = msgText[0]
    # Parse day in format MM-DD

    current_year = datetime.now().year
    try: date_obj = datetime.strptime(f"{current_year}.{day}", "%Y.%m.%d")
    except:
        bot.reply_to(message, telegramify_markdown.markdownify("Дата указана в неправильном формате! Используйте формат `MM.DD`"), parse_mode='MarkdownV2')
        return


    UserTime = date_obj + timedelta(hours=getGmtCorrection(uid))
    now = datetime.now()

    if UserTime < now:
        bot.reply_to(message, "Дата уже прошла!")
        return

    if DayListener.GetListenersCount(uid) >= 3:
        bot.reply_to(message, "Вы достигли максимального количества дневных слушателей!")
        return

    if DayListener.IsDayExists(uid, date_obj):
        bot.reply_to(message, "Данный день уже в списке прослушиваемых дней!")
        return

    DayListener.AddDayListener(uid, date_obj)
    okText = "Информация об этом дне поступит в течении 30 минут после появления расписания! (Beta) Ваш список прослушиваемых дней: \n"
    for day in DayListener.GetDayListenerList(uid):
        okText += "> " + day.strftime("%Y.%m.%d") +"\n"
    bot.reply_to(message, telegramify_markdown.markdownify(okText, max_line_length=None, normalize_whitespace=False), parse_mode='MarkdownV2', disable_notification=True)


@bot.message_handler(commands=['mydaylisteners'])
def myDayListeners(message):
    uid = str(message.chat.id)
    okText = "Ваш список прослушиваемых дней: \n"
    for day in DayListener.GetDayListenerList(uid):
        okText += "> " + day.strftime("%Y.%m.%d") +"\n"
    if len(DayListener.GetDayListenerList(uid)) == 0:
        okText += "Пуст!"
    bot.reply_to(message, telegramify_markdown.markdownify(okText, max_line_length=None, normalize_whitespace=False), parse_mode='MarkdownV2')


@bot.message_handler(commands=['removedaylisteners'])
def removeDayListeners(message):
    uid = str(message.chat.id)
    for day in DayListener.GetDayListenerList(uid):
        DayListener.RemoveDayListener(uid, day)
    bot.reply_to(message, "Ваш список прослушиваемых дней очищен!")


@bot.message_handler(commands=['cleanauthbyid'])
def cleanerById(message):
    uid = str(message.chat.id)
    if not isMessageFromGroup(message):
        if os.path.exists(f'{userFolderPath}/{uid}'):
            keys = message.text.split(" ")
            if len(keys) == 2:
                groupid = keys[1]
                if os.path.exists(f'{userFolderPath}/{groupid}'):
                    userConnectedGroups = ReadFile(f'{uid}/list.inf').split("\n")

                    if groupid in userConnectedGroups and type(groupid) == str:
                        try:
                            groupInt = int(groupid)
                            userConnectedGroups.remove(groupid)
                            SaveFileByList(f'{uid}/list.inf', userConnectedGroups)

                            groupBotData = ReadJSON(f'{groupid}/botInfo.json')
                            groupBotData['login'] = None
                            groupBotData['password'] = None
                            groupBotData['jwtToken'] = None
                            groupBotData['jwtExpiries'] = None
                            SaveJSON(f'{groupid}/botInfo.json', groupBotData)
                            send_message(uid, f"Авторизация для группы *{groupid}* очищена.")
                            send_message(groupInt, "Данные авторизации для этой группы больше не активны. Невозможно запрашивать данные. Пройдите авторизацию с помощью /auth")

                        except Exception as e:
                            send_message(uid, e)

                    else:
                        send_message(uid, "Вы не владеете данными в этой группе. Мы не можем дать доступ к группе")




                else:
                    send_message(uid, "Не можем найти группу проверьте её написание. Сначала выполните команду /start")
            else:
                send_message(uid, "После комманды укажите ID чата группы где вы хотите отвязать авторизацию. Пример: */cleanauthbyid "+uid+"*")
        else:
            send_message(uid, "Не можем найти ваш профиль. Сначала выполните команду /start")
    else:
        bot.reply_to(message, "Вы не можете использовать эту комманду в группах!")


listOfAuthGroups = []
@bot.callback_query_handler(func=lambda call: call.data.startswith("stateGroupAuth"))
def stateGroupAuth(call):
    global listOfAuthGroups
    bot.answer_callback_query(call.id)
    uid = str(call.from_user.id)
    accepted = call.data.split(":")[1]
    groupId = call.data.split(":")[2]
    if accepted == 'True' and not isUserBanned(call.from_user.id):
        if not IsUserRegistered(groupId):
            if IsUserExists(call.from_user.id):
                if IsUserRegistered(call.from_user.id):

                    OriginalUserInfo = ReadBotJson(call.from_user.id)
                    OriginalGroupInfo = ReadBotJson(groupId)
                    OriginalGroupInfo['login'] = OriginalUserInfo['login']
                    OriginalGroupInfo['password'] = OriginalUserInfo['password']
                    OriginalGroupInfo['jwtToken'] = OriginalUserInfo['jwtToken']
                    OriginalGroupInfo['jwtExpiries'] = OriginalUserInfo['jwtExpiries']

                    SaveJSON(groupId + '/botInfo.json', OriginalGroupInfo)

                    listOfAuthGroups = []
                    if not os.path.exists(userFolderPath+'/'+ uid+ '/list.inf'):
                        CreateFile(uid+'/list.inf', groupId)
                        listOfAuthGroups = [groupId]
                    else:
                        listOfAuthGroups = ReadFile(uid+ '/list.inf')
                        listOfAuthGroups = listOfAuthGroups.split("\n")
                        if groupId not in listOfAuthGroups:
                            listOfAuthGroups.append(groupId)
                        SaveFileByList(uid+ '/list.inf', listOfAuthGroups)


                    send_message(call.from_user.id, "Благодарим за активацию данных бота, мы не будем говорить кто активировал бота в группе :)")
                    send_message(groupId, "Бот для этой группы активирован (ID:" + (str(groupId)) + ')', disable_notification=True)
                else:
                    send_message(call.from_user.id, "Ваши данные не зарегистрированы. Пожалуйста, выполните комманду /auth а затем зарегистрируйте бота в группе")
            else:
                send_message(call.from_user.id, "Ваши данные не зарегистрированы. Пожалуйста, выполните комманду /auth")
        else:
            bot.send_message(call.from_user.id, "Кто-то уже привязал группу. Выполнить действие невозможно.")
    else:
        if not isUserBanned(call.from_user.id):
            bot.send_message(call.from_user.id, "Как скажете, но если передумаете - просто нажмите кнопку \"Да\" выше")





    #makeAuth(chat_id, True)





@bot.message_handler(func=lambda message: True)
def echo_message(message):
    uid = str(message.chat.id)
    text = message.text
    ui = ReadBotJson(uid)
    isGroup = isGroupChat(message)

    if not IsUserRegistered(uid) and ui is not None and ui.get('WaitForAuth') == False and not isGroup:
        send_welcome(message)
        return
    if not IsUserRegistered(uid) and isGroup:
        return
    if ui is None:
        send_welcome(message)
        return

    ReAuthInSystem(message)
    ui = ReadBotJson(uid)

    if ui.get('notifySetup'):
        SetWaitForNotify(uid, False)
        SetWaitForLoginData(uid, False)
        args = text.split(" ")
        userTime = args[0].replace(' ','').replace('silent','').replace('.',':').replace('_',':')
        origTime = userTime

        userTime = (datetime.strptime(userTime, "%H:%M") - +timedelta(hours=getGmtCorrection(uid))).strftime("%H:%M")
        if is_valid_time(userTime):
            ###
            cleanNotifyList(uid)
            send_message(uid, "Уведомления успешно активированы. Время уведомлений: " + origTime)

            userBotInfo = ReadJSON(uid + '/botInfo.json')
            additionalDay = 0
            if len(args) > 1:
                additionalDay = args[1]
                userBotInfo['notifyPlus'] = additionalDay
            userBotInfo['notifySilent'] = 'silent' in text
            SaveJSON(uid + '/botInfo.json', userBotInfo)
            clear_user_notify_list(uid)
            add_user_to_notify_list(uid, userTime, additionalDay, 'silent' in text)


            CreateFolderIfNotExists(userFolderPath + '/notifyList/' + is_valid_time(userTime))
            CreateFolderIfNotExists(userFolderPath + '/notifyList/' + is_valid_time(userTime) + '/'+uid)
        else:
            send_message(uid, "Время уведомлений введено некорректно. Пожалуйста, выполните комманду /notifyme снова и введите время в формате HH:MM")


    elif ui.get('WaitForAuth') and not isMessageFromGroup(message):
        # Sometimes happens an error on next line (notifySetup issue)
        login, pasw = text.replace(' ', '').split(',')
        send_message(uid,
                     "Мы выполним вход в ваш аккаунт для проверки пароля. Мы уведомим вас сразу после того как нам придёт ответ от Journal")
        authData = {
            "application_key": '6a56a5df2667e65aab73ce76d1dd737f7d1faef9c52e8b8c55ac75f565d8e8a6',
            "username": login,
            "password": pasw,
        }
        auth = post('https://msapi.top-academy.ru/api/v2/auth/login', authData)
        if auth.status_code == 200:
            responseJson = auth.json()
            userInfo = ReadJSON(uid + '/botInfo.json')
            userInfo['login'] = login
            userInfo['password'] = pasw
            userInfo['jwtToken'] = responseJson.get('access_token')
            userInfo['jwtExpiries'] = responseJson.get('expires_in_access')
            if message.chat.type != 'private':
                userInfo['chat_type'] = message.chat.type
            tkn = responseJson.get('access_token')

            try:
                fullUserInfo = get("https://msapi.top-academy.ru/api/v2/settings/user-info", tkn)
                SaveJSON(uid + '/userInfo.json', fullUserInfo.json())
                userName = fullUserInfo.json()
                if message.chat.type != 'private':
                    userName = "{скрыто}"
                else: userName = userName.get('full_name')


                send_message(uid, "Спасибо за авторизацию в боте, " + userName + '!\n\nТеперь у вас есть возможность запрашивать расписание для вашего Journal. :)')

            except Exception as e:
                print("Error", e)
                send_message(uid, "Мы вошли в ваш аккаунт, но при получении допонительных данных произошла ошибка. Вы можете попробовать ещё раз или игнорировать это.\n(api/v2/settings/u-i: requests.get () error)")

            SaveJSON(uid + '/botInfo.json', userInfo)
            SetWaitForLoginData(uid, False)

        else:
            if auth.status_code == 422:
                send_message(uid,
                             "Journal написал \"Неверный логин или пароль\".\nПроверьте написание логина и пароля в вашем сообщении и пришлите дейтсвующие данные от входа:\n\n```" + login + "```\n```" + pasw + "```")
            else:
                send_message(uid, f"Что-то пошло не так! (Code - {auth.status_code})")
        ui['WaitForAuth'] = False

    elif IsUserRegistered(uid) and not ui.get('WaitForAuth'):
        if True:
            if '!пары' in message.text.lower() or '!gfhs' in message.text.lower() or '!расписание' in message.text.lower():
                fetchDate(message)
            if GetUseTextContext(message.chat.id) and 'пар' in message.text.lower():
                shouldBeExecuted, displayPercent = ContextDetection.GetCommandWeight(message.text)
                if shouldBeExecuted:
                    fetchDate(message)
                else:
                    bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji('☃')],
                                             is_big=False)
                    if not os.path.exists('notTriggeredTexts.txt'):
                        open('notTriggeredTexts.txt', 'w+').close()

                    file = open('notTriggeredTexts.txt', 'a+', encoding="utf-8")
                    file.write(f'"{message.text.lower()}"  >>>  {round(displayPercent, 3)}\n')
                    file.close()



@bot.message_handler(commands=['dynamicmessage'])
def DynamicMessage(message):
    uid = str(message.chat.id)
    forum = isForum(message)
    botin = ReadJSON(uid + '/botInfo.json')
    DynamicChatID = botin.get('DynamicChatID')
    DynamicForumID = botin.get('DynamicForumID')
    DynamicChatMessage = botin.get('DynamicID')
    Message = None
    if DynamicChatMessage is None or DynamicForumID is None or DynamicChatID is None:
        Message = bot.send_message(uid, text="Пару минут...", message_thread_id=forum)
        DynamicChatMessage, botin['DynamicID'] = 2 * [Message.message_id]
        DynamicChatID, botin['DynamicChatID'] = 2 * [uid]
        DynamicForumID, botin['DynamicForumID'] = 2 * [forum]
        SaveJSON(uid+'botInfo.json', botin)






@bot.callback_query_handler(func=lambda call: call.data == "ok_pressed")
def callback_ok(call):
    # Показываем попап с текстом при нажатии на кнопку
    bot.answer_callback_query(callback_query_id=call.id, text="Пример текста", show_alert=True)



def send_message(userId, msg, reply_markup=None, disable_notification=False, message_thread_id=None):
    converted = telegramify_markdown.markdownify(
        msg,
        max_line_length=None,
        normalize_whitespace=False,

    )
    return bot.send_message(userId, converted, parse_mode='MarkdownV2', reply_markup=reply_markup, disable_notification = disable_notification, message_thread_id=message_thread_id)


print("Bot is running...")
while True:
    try:
        bot.infinity_polling()
        print("Pooled")
    except Exception as e:
        print(f"Ошибка подключения: {e} Relaunching...")

    time.sleep(1)
