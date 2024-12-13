from threading import *
from telebot.types import ReactionTypeEmoji
import telegramify_markdown
from telegramify_markdown import customize
from dateProcessor import *
import logging
import json
import os
from databases import *
import time
from datetime import datetime, timedelta
import requests
import telebot
import shutil
from telebot import types


#Version 1.1


def isForum(message):
    forum = message.json['chat'].get("is_forum")
    if forum and message.message_thread_id is not None:
        forum = message.message_thread_id
    return forum

logFile = "botLogs.txt"

if os.path.exists(logFile):
    os.remove(logFile)

# Настройка логирования
logging.basicConfig(
    filename=logFile,
    level=logging.DEBUG,          # Уровень логирования (DEBUG для записи всех событий)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
    datefmt='%Y-%m-%d %H:%M:%S'   # Формат времени
)

userFolderPath = 'userInfo'

API_TOKEN = open('tkn.ini', 'r').read()
bot = telebot.TeleBot(API_TOKEN)
logger = logging.getLogger('TeleBot').setLevel(logging.INFO)

hoursCalibration = 4

moscowTime = datetime.now()+timedelta(hours=hoursCalibration)

def reInitTime():
    global moscowTime
    moscowTime = datetime.now()+timedelta(hours=hoursCalibration)


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

def cleanNotifyList(uid):
    for time in os.listdir(userFolderPath+'/notifyList/'):
        for userId in os.listdir(userFolderPath+'/notifyList/'+time):
            if userId == uid:
                os.rmdir(userFolderPath+'/notifyList/'+time+'/'+userId)
                send_message(uid, "*Notifier*: \nУведомления для времени \""+time.replace("_",":")+"\" отключены", disable_notification=True)

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
            print("currentTime: " + mscTime)
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

    if UserRegister(message.chat.id, message.chat.type) == False:
        keyboard = types.InlineKeyboardMarkup()

        if isMessageFromGroup(message) == False:
            auth_button = types.InlineKeyboardButton(text="Авторизоваться", callback_data=f"auth:{message.chat.id}")
            keyboard.add(auth_button)
            bot.send_message(message.chat.id,
                text="Привет! Этот бот показывает расписание для вашего аккунта в Journal. Для этого нужна авторизация вашего аккунта в боте.",
                reply_markup=keyboard, message_thread_id=forum)
        else:


            additionalText = '\n\nID Группы: `'+str(message.chat.id)+'`.\nЗапомните ID выше и нажмите кнопку ниже, чтобы авторизовать бота в группе через личные сообщения (Обычная авторизация в группе недоступна из-за соображений безопасности).'
            send_message(message.chat.id,
                         "Привет! Этот бот показывает расписание для вашего аккунта в Journal. Для этого нужна авторизация вашего аккунта в боте. " + additionalText, message_thread_id=forum)

            keyboard = types.InlineKeyboardMarkup()
            auth_button = types.InlineKeyboardButton(text="Авторизовать группу", callback_data=f"groupAuth:{message.chat.id}")
            keyboard.add(auth_button)
            send_message(message.chat.id, "*Для нормальной работы бота выдайте ему роль администраотра*\n*Для того чтобы кнопка работала напишите ему в личные сообщения*\n\nАвторизация не доступна в группе. Используйте кнопку ниже для привязки аккаунту к группе:", reply_markup=keyboard, message_thread_id=forum)


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


@bot.message_handler(commands=['auth'])
def makeAuth(message, messageIsAnId=False):



    if messageIsAnId==False and isMessageFromGroup(message):
        if isUserBanned(message):
            send_message(message.chat.id, "\{ banned: true \}")
            return

        if IsUserRegistered(message.chat.id) == False:
            send_welcome(message)
            return
        else:
            send_message(message.chat.id, "Группа уже имеет данные авторизации. Вы можете авторизоваться заново используя /clearauth а затем /auth.")
            return


    user = message
    if type(message) is int:
        user = message

    if IsUserExists(user) == False:
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
        """)
    ui = ReadBotJson(user)
    ui['WaitForAuth'] = True
    SaveJSON(user + '/botInfo.json', ui)


@bot.callback_query_handler(func=lambda call: call.data.startswith("auth"))
def auth_callback(call):
    bot.answer_callback_query(call.id)
    data = call.data.split(":")
    chat_id = data[1]
    makeAuth(chat_id, True)

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
*/notifyme* - Настроить ежедневную отправку расписания в формате часы:минуты

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


def ReAuthInSystem(message):
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
            if message.chat.type != 'private':
                userInfo['chat_type'] = message.chat.type
            SaveJSON(uid + '/botInfo.json', userInfo)
            return tkn
        else:
            return auth.status_code
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



@bot.message_handler(commands=['passnotify'])
def cancelNotify(message):
    uid = str(message.chat.id)
    clear_user_notify_list(uid)
    cleanNotifyList(uid)


@bot.message_handler(commands=['whatTimeForBot'])
def whatTimeForBot(message):
    uid = str(message.chat.id)
    bot.send_message(uid, str(moscowTime.strftime("%H_%M")))


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



@bot.message_handler(commands=['пары', 'расписание', 'sched', 'shed'])
def fetchDate(message, Relaunch=False, Sended=None):
    uid = str(message.chat.id)
    forum = isForum(message)

    if IsUserRegistered(uid):

        if isUserBanned(message.from_user.id):
            return


        bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji('👀')], is_big=False)


        global showingText
        global operationDay
        sended_msg = Sended
        if Relaunch == False:
            sended_msg = send_message(uid, "Секунду, ищем расписание...", disable_notification=True, message_thread_id=forum)

        uiInfo = ReadBotJson(uid)
        expiration_timestamp = uiInfo.get('jwtExpiries')
        lastJwt = uiInfo.get('jwtToken')
        basicUrl = 'https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter='
        operationDay = datetime.today()
        showingText = "сегодня"

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

        if "послезавтра" in message.text.lower():
            showingText = "послезавтра"
            operationDay = operationDay+timedelta(days=2)
        elif "завтра" in message.text.lower():
            showingText = "завтра"
            operationDay = operationDay + timedelta(days=1)
        elif "вчера" in message.text.lower():
            showingText = "вчера"
            operationDay = operationDay-timedelta(days=1)


        if type(operationDay) != str:
            operationDay = operationDay.strftime('%Y-%m-%d')


        if expiration_timestamp is None:
            expiration_timestamp = time.time()+10

        if time.time() < expiration_timestamp:
            #JWT Key Is Still Valid
            # Example of url by finding a day:
            #https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter= YYYY - MM - DD


            fetchResult = get(basicUrl+operationDay, lastJwt)
            if fetchResult.status_code == 200:
                jsonResult = fetchResult.json()

                finalText = ""
                for lesson in jsonResult:

                    finalText += '>*Пара ' + str(lesson.get('lesson')) + ':  '+lesson.get('teacher_name')+'*\n'
                    finalText += '```\n' + lesson.get('subject_name') + "\n"
                    finalText += lesson.get('started_at')+" - "+lesson.get('finished_at')+" ("+lesson.get('room_name')+")\n"
                    finalText += "```\n"


                if sended_msg is not None:
                    try:
                        bot.edit_message_text(chat_id=message.chat.id, message_id=sended_msg.message_id, text="Пары на *" + showingText + "*:\n\n" +finalText, parse_mode='MarkdownV2')
                        return
                    except: pass


                if len(finalText) == 0:
                    finalText="В этот день ничего нет :D"

                converted = telegramify_markdown.markdownify(
                    finalText,
                    max_line_length=None,
                    normalize_whitespace=False
                )
                showingText = showingText.replace("-", "\\-")
                try:
                    bot.edit_message_text(chat_id=message.chat.id, message_id=sended_msg.message_id, text="Пары на *" + showingText + "*:\n\n" + converted, parse_mode='MarkdownV2')
                except:
                    bot.send_message(message.chat.id, text="Пары на *" + showingText + "*:\n\n" + converted, parse_mode='MarkdownV2', message_thread_id=forum)
            else:
                ReAuthInSystem(message)
                if not Relaunch:
                    bot.delete_message(message_id=sended_msg.message_id, chat_id=message.chat.id)
                    fetchDate(message, True, sended_msg)
                else:
                    bot.send_message(message.chat.id, text="Не удалось загрузить расписание. Что-то с JWT ключом...", parse_mode='MarkdownV2', message_thread_id=forum)
        else:
            ReAuthInSystem(message)

            if not Relaunch:
                bot.delete_message(message_id=sended_msg.message_id, chat_id=message.chat.id)
                fetchDate(message, True, sended_msg)
            else:
                bot.send_message(message.chat.id, text="Не удалось загрузить расписание. Что-то с JWT ключом...", parse_mode='MarkdownV2', message_thread_id=forum)



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


@bot.message_handler(commands=['cleanauthbyid'])
def cleanerById(message):
    uid = str(message.chat.id)
    if not isMessageFromGroup(message):
        if os.path.exists(userFolderPath + '/' + uid):
            keys = message.text.split(" ")
            if len(keys) == 2:
                groupid = keys[1]
                if os.path.exists(userFolderPath + '/' + groupid):
                    userConnectedGroups = ReadFile(uid+'/list.inf').split("\n")

                    if groupid in userConnectedGroups and type(groupid) == str:
                        try:
                            groupInt = int(groupid)
                            userConnectedGroups.remove(groupid)
                            SaveFileByList(uid+'/list.inf', userConnectedGroups)

                            groupBotData = ReadJSON(groupid+'/botInfo.json')
                            groupBotData['login'] = None
                            groupBotData['password'] = None
                            groupBotData['jwtToken'] = None
                            groupBotData['jwtExpiries'] = None
                            SaveJSON(groupid+'/botInfo.json', groupBotData)
                            send_message(uid, "Авторизация для группы *"+groupid+"* очищена.")
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


                    send_message(call.from_user.id, "Благодарим за активацию данных бота, мы постараемся не говорить кто активировал бота в группе :)")
                    send_message(groupId, "Кто-то успешно зарегестрировал бота в группе (ID:" + (str(groupId)) + ')', disable_notification=True)
                else:
                    send_message(call.from_user.id, "Ваши данные не зарегистрированы. Пожалуйста, выполните комманду /auth а затем зарегистрируйте бота в группе")
            else:
                send_message(call.from_user.id, "Ваши данные не зарегистрированы. Пожалуйста, выполните комманду /auth")
        else:
            bot.send_message(call.from_user.id, "Кто-то уже привязал группу. Выполнить действие невозможно.")
    else:
        if not isUserBanned(call.from_user.id):
            bot.send_message(call.from_user.id, "Как скажете, если передумаете - просто нажмите кнопку \"Да\" выше")





    #makeAuth(chat_id, True)


def get(url, authToken=None):
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


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    uid = str(message.chat.id)
    text = message.text
    ui = ReadBotJson(uid)

    if not IsUserRegistered(uid) and ui is not None and ui.get('WaitForAuth') == False:
        send_welcome(message)
        return
    if ui is None:
        send_welcome(message)
        return

    ui = ReadBotJson(uid)

    if ui.get('notifySetup'):
        SetWaitForNotify(uid, False)
        SetWaitForLoginData(uid, False)
        args = text.split(" ")
        userTime = args[0].replace(' ','').replace('silent','').replace('.',':').replace('_',':')

        if is_valid_time(userTime):
            ###
            cleanNotifyList(uid)
            send_message(uid, "Уведомления успешно активированы. Время уведомлений: " + userTime)

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
                send_message(uid, "Мы вошли в ваш аккаунт, но при получении допонительных данных произошла ошибка. Вы можете попробовать ещё раз или игнорировать это.\n(api/v2/settings/u-i: get() error)")

            SaveJSON(uid + '/botInfo.json', userInfo)
            SetWaitForLoginData(uid, False)

        else:
            if auth.status_code == 422:
                send_message(uid,
                             "Journal написал \"Неверный логин или пароль\".\nПроверьте написание логина и пароля в вашем сообщении и пришлите дейтсвующие данные от входа:\n\n```" + login + "```\n```" + pasw + "```")
            else:
                send_message(uid, "Что-то пошло не так!")
        ui['WaitForAuth'] = False

    elif IsUserRegistered(uid) and not ui.get('WaitForAuth'):
        if True:
            if '!пары' in message.text.lower() or '!gfhs' in message.text.lower() or '!расписание' in message.text.lower():
                fetchDate(message)



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



while True:
    try:
        bot.infinity_polling()
        print("Pooled")
    except Exception as e:
        logging.error(f"Ошибка подключения: {e} Relaunching...")

    time.sleep(1)
