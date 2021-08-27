# coded by @lytk4dev

"""
План:
События в чате
Аттачменты
Стикеры из телеги

"""

import vk_api, telebot, json
from threading import Thread
from vk_api.longpoll import VkLongPoll

data=json.loads(open("data.json", "r").read())
chats=json.loads(open("chats.json", "r").read())

current_chat=0

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

@tg_session.message_handler(commands=['switch'])
def switch(message):
    global current_chat
    if chats[message.text.split()[1]] != None:
        current_chat=vk_session.method("users.get", {"user_ids":chats[message.text.split()[1]]})[0]["id"]
        print(current_chat)
        tg_session.send_message(message.chat.id,f"Чат сменен на {message.text.split()[1]}")
    else:
        tg_session.send_message(message.chat.id,"Такого чата в базе нет")

@tg_session.message_handler(content_types=["text"])
def send(message):
    vk.messages.send(user_id=current_chat,random_id=0,message=message.text)

def vk_work():
    print("VK loaded")
    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        try:
            sender=vk.users.get(user_ids=event.user_id)
            #vk_session.method("messages.getChat", {"chat_id": event.chat_id})["title"]
            #print(f"{sender[0]['first_name']} {sender[0]['last_name']} | {event.message}")
            #print(event.message_id)
            #print(dir(vk_session.method('messages.getById', {"messages_ids":event.message_id,"preview_length":0})))
            if event.from_chat == True and event.from_me == False and event.message_id != None:
                #print(event.message_id)
                if "reply_message" in vk.messages.getById(message_ids=event.message_id)['items'][0]:
                    reply = vk.messages.getById(message_ids=event.message_id)['items'][0]['reply_message']
                    user = vk.users.get(user_ids=reply["from_id"])[0]
                    print(user)
                    tg_session.send_message(data["tg_id"],f"*{vk_session.method('messages.getChat', {'chat_id': event.chat_id})['title']}* | {user['first_name']} {user['last_name']}: {reply['text']} | {sender[0]['first_name']} {sender[0]['last_name']}: {event.message}", parse_mode='Markdown')
                else:
                    tg_session.send_message(data["tg_id"],f"*{vk_session.method('messages.getChat', {'chat_id': event.chat_id})['title']}* | {sender[0]['first_name']} {sender[0]['last_name']}: {event.message}", parse_mode='Markdown')
            if event.from_me == False and event.from_user == True and event.message_id != None:
                if "reply_message" in vk.messages.getById(message_ids=event.message_id)['items'][0]:
                    reply = vk.messages.getById(message_ids=event.message_id)['items'][0]['reply_message']
                    user = vk.users.get(user_ids=reply["from_id"])[0]
                    tg_session.send_message(data["tg_id"],f"{user['first_name']} {user['last_name']}: {reply['text']} | {sender[0]['first_name']} {sender[0]['last_name']}: {event.message}", parse_mode='Markdown')
                else:
                    tg_session.send_message(data["tg_id"],f"{sender[0]['first_name']} {sender[0]['last_name']}: {event.message}")
        except: 
            pass

Thread(target=vk_work).start()
Thread(target=tg_session.polling).start()
