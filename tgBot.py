import logging
import json
import os
import time
from datetime import datetime, timedelta
import requests
import telebot
import shutil
from telebot import types

userFolderPath = 'userInfo'

API_TOKEN = open('tkn.ini', 'r').read()
bot = telebot.TeleBot(API_TOKEN)
logger = logging.getLogger('TeleBot').setLevel(logging.INFO)




def CreateFolderIfNotExists(path):
    if os.path.exists(path) != True:
        os.mkdir(path)


CreateFolderIfNotExists(userFolderPath)

def IsUserExists(userId):
    userId = str(userId)
    return os.path.exists(userFolderPath + '/' + userId)

def ReadBotJson(userId):
    userId = str(userId)
    pathToJson = userFolderPath + '/' + userId + '/botInfo.json'
    file = open(pathToJson, 'r', encoding='utf-8')
    return json.loads(file.read())


def ReadJSON(pathToJson):
    pathToJson = userFolderPath + '/' + pathToJson
    file = open(pathToJson, 'r', encoding='utf-8')
    return json.loads(file.read())


def SaveJSON(pathToJson, savingJSON):
    pathToJson = userFolderPath + '/' + pathToJson
    with open(pathToJson, 'w', encoding='utf-8') as f:
        json.dump(savingJSON, f, ensure_ascii=False, indent=4)


def IsUserRegistered(userId):
    if IsUserExists(userId):
        userId = str(userId)
        reg = ReadBotJson(userId)
        return (reg.get('login') != None and reg.get('password') != None)
    else:
        return False

def SetWaitForLoginData(userId, state):
    userId = str(userId)
    reg = ReadBotJson(userId)
    reg['WaitForAuth'] = state
    SaveJSON(userId + '/botInfo.json', reg)

def dictToJson(d):
    return json.dumps(d)

def isMessageFromGroup(msg):
    return msg.chat.type != 'private'

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
    if UserRegister(message.chat.id, message.chat.type) == False:
        keyboard = types.InlineKeyboardMarkup()

        if isMessageFromGroup(message) == False:
            auth_button = types.InlineKeyboardButton(text="Авторизоваться", callback_data=f"auth:{message.chat.id}")
            keyboard.add(auth_button)
            bot.send_message(message.chat.id,
                             text="Привет! Этот бот показывает расписание для вашего аккунта в Journal. Для этого нужна авторизация вашего аккунта в боте.",
                             reply_markup=keyboard)
        else:


            additionalText = '\n\nID Группы: `'+str(message.chat.id)+'`.\nЗапомните ID выше и нажмите кнопку ниже, чтобы авторизовать бота в группе через личные сообщения (Обычная авторизация в группе недоступна из-за соображений безопасности).'
            send_message(message.chat.id,
                         "Привет! Этот бот показывает расписание для вашего аккунта в Journal. Для этого нужна авторизация вашего аккунта в боте. " + additionalText)

            keyboard = types.InlineKeyboardMarkup()
            auth_button = types.InlineKeyboardButton(text="Авторизовать группу", callback_data=f"groupAuth:{message.chat.id}")
            keyboard.add(auth_button)
            send_message(message.chat.id, "*Для нормальной работы бота выдайте ему роль администраотра*\n*Для того чтобы кнопка работала напишите ему в личные сообщения*\n\nАвторизация не доступна в группе. Используйте кнопку ниже для привязки аккаунту к группе:", reply_markup=keyboard)


# Функция для проверки прав администратора
def is_admin(chat_id):
    member = bot.get_chat_member(chat_id, bot.get_me().id)
    return member.status in ['administrator', 'creator']

@bot.message_handler(commands=['clearauth'])
def clearAuth(message):
    uid = str(message.chat.id)
    if os.path.exists(userFolderPath + '/' + uid):
        shutil.rmtree(userFolderPath+'/'+uid)
        send_message(uid, "Авторизация очищена. Чтобы привязать данные авторизации используйте /auth")


@bot.message_handler(commands=['cancelauth'])
def clearAuth(message):
    uid = str(message.chat.id)
    UserInfo = ReadBotJson(uid)
    UserInfo['WaitForAuth'] = False
    SaveJSON(uid + '/botInfo.json', UserInfo)
    send_message(uid, "Авторизация отменена. Чтобы привязать данные авторизации используйте /auth")


@bot.message_handler(commands=['auth'])
def makeAuth(message, messageIsAnId=False):
    if messageIsAnId==False and isMessageFromGroup(message):
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

    SetWaitForLoginData(user, True)
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
    if IsUserExists(whoClicked):
        if IsUserRegistered(whoClicked):
            if not IsUserRegistered(data[1]):
                SetWaitForLoginData(whoClicked, False)
                keyboard = types.InlineKeyboardMarkup()
                yesButton = types.InlineKeyboardButton(text="Да", callback_data=f"stateGroupAuth:True:"+data[1])
                noButton = types.InlineKeyboardButton(text="Отмена", callback_data=f"stateGroupAuth:False:"+data[1])
                keyboard.add(yesButton)
                keyboard.add(noButton)
                send_message(whoClicked, "Подтвердите, что вы хотите авторизоваться в группе \nID: `" + (str(data[1])) + '`\n\n Нажимая кнопку "Да" вы соглашаетесь с тем что ваши данные Journal будут использованы для группы.',reply_markup=keyboard)
            else:
                send_message(whoClicked, "Вы не можете авторизовать группу так как она уже кем то авторизована. Напищите в группе комманду `/clearauth` для привязки ваших данных к группе")
        else:
            send_message(whoClicked, "Ваши данные не зарегистрированы. Пожалуйста, сперва сначала пройдите процесс авторизации /auth")
    else:
        try:
            send_message(whoClicked, "Чтобы авторизоваться в группе, необходимо зарегистрироваться ваш Telegram аккаунт в боте.\n\nДля этого нужно использовать комманду /auth")
        except:
            pass


@bot.message_handler(commands=['пары', 'расписание'])
def fetchDate(message):
    uid = str(message.chat.id)
    print('shedulecall: ',message)
    if IsUserRegistered(uid):
        global showingText
        global operationDay
        sended_msg = send_message(uid, "Секунду, ищем расписание...")
        uiInfo = ReadBotJson(uid)
        expiration_timestamp = uiInfo.get('jwtExpiries')
        lastJwt = uiInfo.get('jwtToken')
        basicUrl = 'https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter='
        operationDay = datetime.today()
        showingText = "сегодня"


        if "послезавтра" in message.text.lower():
            showingText = "послезавтра"
            operationDay = operationDay+timedelta(days=2)
        elif "завтра" in message.text.lower():
            showingText = "завтра"
            operationDay = operationDay + timedelta(days=1)

        if "вчера" in message.text.lower():
            showingText = "вчера"
            operationDay = operationDay-timedelta(days=1)
        if "-" in message.text:
            showingText = message.text
            operationDay = datetime.strptime(message.text, "%Y-%m-%d")
            print("Detected \"-\" in:", showingText)







        operationDay = operationDay.strftime('%Y-%m-%d')
        if expiration_timestamp == None:
            expiration_timestamp = time.time()+10

        if time.time() < expiration_timestamp:
            #JWT Key Is Still Valid
            # Example of url by finding a day:
            #https://msapi.top-academy.ru/api/v2/schedule/operations/get-by-date?date_filter= YYYY - MM - DD

            print('fetching:', basicUrl+operationDay)
            print('jwt:', lastJwt)
            fetchResult = get(basicUrl+operationDay, lastJwt)
            jsonResult = fetchResult.json()
            print('endedFetch:', lastJwt)

            finalText = ""
            for lesson in jsonResult:
                finalText += '```Пара'+str(lesson.get('lesson'))+':\n'+ lesson.get('subject_name')+"\n"
                finalText += lesson.get('started_at')+" - "+lesson.get('finished_at')+" ("+lesson.get('room_name')+")\n"
                finalText += "```"
            print('Trying to edit msg')
            bot.delete_message(message_id=sended_msg.message_id, chat_id=message.chat.id)
            bot.send_message(message.chat.id, text="Пары на `"+operationDay+"`:\n\n"+finalText, parse_mode='MarkdownV2')
            print('Edited!')
        else:
            print(expiration_timestamp)
            print(lastJwt)
            print(time.time() < expiration_timestamp)






@bot.callback_query_handler(func=lambda call: call.data.startswith("stateGroupAuth"))
def stateGroupAuth(call):
    bot.answer_callback_query(call.id)
    accepted = call.data.split(":")[1]
    groupId = call.data.split(":")[2]
    if accepted == 'True':
        if not IsUserRegistered(groupId):
            if IsUserExists(call.from_user.id):
                if IsUserRegistered(call.from_user.id):

                    OriginalUserInfo = ReadBotJson(call.from_user.id)
                    OriginalGroupInfo = ReadBotJson(groupId)
                    OriginalGroupInfo['login'] = OriginalUserInfo['login']
                    OriginalGroupInfo['password'] = OriginalUserInfo['password']
                    SaveJSON(groupId + '/botInfo.json', OriginalGroupInfo)
                    send_message(call.from_user.id, "Благодарим за активацию данных бота, мы постараемся не говорить кто активировал бота в группе :)")
                    send_message(groupId, "Кто-то успешно зарегестрировал бота в группе (ID:" + (str(groupId)) + ')')
                else:
                    send_message(call.from_user.id, "Ваши данные не зарегистрированы. Пожалуйста, выполните комманду /auth а затем зарегистрируйте бота в группе")
            else:
                send_message(call.from_user.id, "Ваши данные не зарегистрированы. Пожалуйста, выполните комманду /auth")
        else:
            bot.send_message(call.from_user.id, "Кто-то уже привязал группу. Выполнить действие невозможно.")
    else:
        bot.send_message(call.from_user.id, "Отмена")





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
    print(message)

    text = message.text
    ui = ReadBotJson(uid)
    if ui.get('WaitForAuth') and not isMessageFromGroup(message):
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

            if True:
                fullUserInfo = get("https://msapi.top-academy.ru/api/v2/settings/user-info", tkn)
                SaveJSON(uid + '/userInfo.json', fullUserInfo.json())
                userName = fullUserInfo.json()
                if message.chat.type != 'private':
                    userName = "{скрыто}"
                else: userName = userName.get('full_name')

                send_message(uid,
                    "Спасибо за авторизацию в боте, " + userName + '!\n\nТеперь у вас есть возможность запрашивать расписание для вашего Journal. :)')
            # except Exception as e:
            #    print("Error", e)
            #    send_message(uid, "Мы вошли в ваш аккаунт, но при получении допонительных данных произошла ошибка. Вы можете попробовать ещё раз или игнорировать это.\n(api/v2/settings/u-i: get() error)")

            SaveJSON(uid + '/botInfo.json', userInfo)

        else:
            if auth.status_code == 422:
                send_message(uid,
                             "Journal написал \"Неверный логин или пароль\".\nПроверьте написание логина и пароля в вашем сообщении и пришлите дейтсвующие данные от входа:\n\n```" + login + "```\n```" + pasw + "```")
            else:
                send_message(uid, "Что-то пошло не так!")
        ui['WaitForAuth'] = False


@bot.callback_query_handler(func=lambda call: call.data == "ok_pressed")
def callback_ok(call):
    # Показываем попап с текстом при нажатии на кнопку
    bot.answer_callback_query(callback_query_id=call.id, text="Пример текста", show_alert=True)


def send_message(userId, msg, reply_markup=None):
    msg = msg.replace("-", "\\-").replace(".", "\\.").replace("!", "\\!").replace("(", "\\(").replace(")", "\\)")
    return bot.send_message(userId, msg, parse_mode='MarkdownV2', reply_markup=reply_markup)


bot.infinity_polling()

