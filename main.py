# coded by @lytk4dev

"""
План:
События в чате
Аттачменты
Стикеры из телеги

"""

import vk_api, telebot, json
from telebot import types
from threading import Thread
from vk_api.longpoll import VkLongPoll

data=json.loads(open("data.json", "r").read())
chats=json.loads(open("chats.json", "r").read())

current_chat=0

isChat = False
tg_token=None
tg_session = telebot.TeleBot(data["tg_token"])

tg_id=0

vk_session = vk_api.VkApi(token=data["vk_token"])
vk = vk_session._auth_token()
vk = vk_session.get_api()

def registraion(message, tg_id):
    data["tg_id"]=message.chat.id
    data_file = open("data.json", "w").write(json.dumps(data))
    tg_session.reply_to(message, f"Привязка к ID: {data['tg_id']}")
    tg_id=message.chat.id

@tg_session.message_handler(commands=['start'])
def start(message):
    global tg_id
    if "password" in data:
        if data["password"] == message.text.split()[1]:
            registraion(message, message.chat.id)
        else:
            tg_session.send_message(message.chat.id,"Пароль неверный")
    else:
        registraion(message, message.chat.id)

@tg_session.message_handler(commands=['chats'])
def switch(message): # вывод клавиатуры с списком чатов из chats.json
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    buttons=[]
    for i in chats.keys():
        buttons.append(f"/switch {i}")
    keyboard.add(*buttons)
    tg_session.send_message(message.chat.id, "Выберите чат", reply_markup=keyboard)
    keyboard = types.ReplyKeyboardRemove()

# vk.messages.send(peer_id=2000000242, random_id=0,message="Привет")

@tg_session.message_handler(commands=['switch'])
def switch(message): # смена чата
    global isChat
    global current_chat
    try:
        if chats[message.text.split()[1]] != None and "_chat" not in message.text:
            current_chat=vk_session.method("users.get", {"user_ids":chats[message.text.split()[1]]})[0]["id"]
            tg_session.send_message(message.chat.id,f"Чат сменен на {message.text.split()[1]}")
            isChat=False
        elif chats[message.text.split()[1]] != None and "_chat" in message.text:
            current_chat=2000000000+int(chats[message.text.split()[1]])
            isChat=True
            tg_session.send_message(message.chat.id,f"Чат сменен на {message.text.split()[1]}")
        else:
            tg_session.send_message(message.chat.id,"Такого чата в базе нет")
    except:
        tg_session.send_message(message.chat.id,f"Что-то упало :(")

@tg_session.message_handler(content_types=["text"])
def send(message):
    if message.text[0] != "/" and message.text[0] != "!" and isChat==False:
        vk.messages.send(user_id=str(current_chat),random_id=0,message=str(message.text))
    elif message.text[0] != "/" and message.text[0] != "!" and isChat==True:
        vk.messages.send(peer_id=str(current_chat),random_id=0,message=str(message.text))
    else:
        print(message.text)


def get_reply(message_data):
    replier = vk.users.get(user_ids=message_data['reply_message']["from_id"])[0]
    return f"{replier['first_name']} {replier['last_name']}: {message_data['reply_message']['text']}"

def vk_work(): # Вся магия здесь
    print("VK loaded")
    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        try:
            if event.message_id != None:
                message_data = vk.messages.getById(message_ids=event.message_id)['items'][0]
                sender=vk.users.get(user_ids=event.user_id)[0]
                if event.from_chat == True and event.from_me == False: # Сообщение из беседы
                    chat_title=vk_session.method('messages.getChat', {'chat_id': event.chat_id})['title']
                    if "reply_message" in message_data: # Ответ на сообщение
                        tg_session.send_message(data["tg_id"],f"*{chat_title}* | {get_reply(message_data)} |{sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
                    else: # Обычный случай
                        tg_session.send_message(data["tg_id"],f"*{chat_title}* | {sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
                if event.from_me == False and event.from_user == True: # Сообщение из лички
                    if "reply_message" in vk.messages.getById(message_ids=event.message_id)['items'][0]: 
                        tg_session.send_message(data["tg_id"],f"{get_reply(message_data)} | {sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
                    else:
                        tg_session.send_message(data["tg_id"],f"{sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
        except Exception as err: 
            print(err)

Thread(target=vk_work).start()
Thread(target=tg_session.polling).start()
