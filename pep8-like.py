import vk_api
import telebot
import json
from telebot import types
from threading import Thread
from vk_api.longpoll import VkLongPoll
from loguru import logger
import sys

logger.configure(handlers=[{"sink": sys.stderr, "format": "{time} {level} {function} {message}  "}])

data = json.loads(open("data.json", "r").read())
chats = json.loads(open("chats.json", "r").read())

current_chat = 0

isChat = False
tg_token = None
tg_session = telebot.TeleBot(data["tg_token"])

tg_id = 0

vk_session = vk_api.VkApi(token=data["vk_token"])
vk = vk_session._auth_token()
vk = vk_session.get_api()


def registration(message, tg_id):
    try:
        data["tg_id"] = message.chat.id
        data_file = open("data.json", "w").write(json.dumps(data))
        tg_session.reply_to(message, f"Привязка к ID: {data['tg_id']}")
        tg_id = message.chat.id
        logger.info(f"Telegram ID for the current chat updated, new ID: {tg_id}")
    except Exception as e:
        logger.error(f"Error during the registration process: {e}")


@tg_session.message_handler(commands=['start'])
def start(message):
    global tg_id
    try:
        if "password" in data:
            if data["password"] == message.text.split()[1]:
                registration(message, message.chat.id)
                logger.info(f"User with ID {message.chat.id} successfully authenticated with a password.")
            else:
                tg_session.send_message(message.chat.id, "Пароль неверный")
                logger.info(f"User with ID {message.chat.id} failed to authenticate with a password.")
        else:
            registration(message, message.chat.id)
            logger.info(f"User with ID {message.chat.id} registered without a password.")
    except Exception as e:
        logger.error(f"Error in the start function for the user with ID {message.chat.id}: {e}")


@tg_session.message_handler(commands=['chats'])
def switch(message):  # вывод клавиатуры с списком чатов из chats.json
    try:
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
        buttons = []
        for i in chats.keys():
            buttons.append(f"/switch {i}")
        keyboard.add(*buttons)
        tg_session.send_message(message.chat.id, "Выберите чат", reply_markup=keyboard)
        logger.info(f"Keyboard with chat options is available to the user with ID: {message.chat.id}")
    except Exception as e:
        logger.error(f"Error in the switch function for the user with ID {message.chat.id}: {e}")
        tg_session.send_message(message.chat.id, "Что-то упало :( Возможно вы не указали чаты в chats.json",
                                reply_markup=keyboard)

@tg_session.message_handler(commands=['switch'])
def switch(message):  # смена чата
    global isChat
    global current_chat
    try:
        if chats[message.text.split()[1]] is not None and "_chat" not in message.text:
            current_chat = vk_session.method("users.get", {"user_ids": chats[message.text.split()[1]]})[0]["id"]
            tg_session.send_message(message.chat.id, f"Чат сменен на {message.text.split()[1]}")
            isChat = False
            logger.info(f"User with ID {message.chat.id} switched to a chat: {message.text.split()[1]}")
        elif chats[message.text.split()[1]] is not None and "_chat" in message.text:
            current_chat = 2000000000 + int(chats[message.text.split()[1]])
            isChat = True
            tg_session.send_message(message.chat.id, f"Чат сменен на {message.text.split()[1]}")
            logger.info(f"User with ID {message.chat.id} switched to a group chat: {message.text.split()[1]}")
        else:
            tg_session.send_message(message.chat.id, "Такого чата в базе нет")
            logger.warning(f"User with ID {message.chat.id} attempted to switch to an unknown chat: {message.chat.id}")
    except Exception as e:
        tg_session.send_message(message.chat.id, "Что-то упало :(")
        logger.error(f"Error during switching chat for the user with ID {message.chat.id}: {e}")


@tg_session.message_handler(content_types=["text"])
def send(message):
    try:
        if message.text[0] != "/" and message.text[0] != "!" and not isChat:
            vk.messages.send(user_id=str(current_chat), random_id=0, message=str(message.text))
            logger.info(f"Message sent to VK user: {current_chat}")
        elif message.text[0] != "/" and message.text[0] != "!" and isChat:
            vk.messages.send(peer_id=str(current_chat), random_id=0, message=str(message.text))
            logger.info(f"Message sent to VK group chat: {current_chat}")
    except Exception as e:
        logger.error(f"Error sending message to VK: {e}")


def get_reply(message_data):
    try:
        replier = vk.users.get(user_ids=message_data['reply_message']["from_id"])[0]
        logger.info(f"Reply generated: {replier['first_name']} {replier['last_name']}: {message_data['reply_message']['text']}")
        return f"{replier['first_name']} {replier['last_name']}: {message_data['reply_message']['text']}"
    except Exception as e:
        logger.error(f"Error in get_reply function: {e}")
        return "Ошибка при формировании ответа"


def vk_work():  # Вся магия здесь
    logger.info("VK loaded")
    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        try:
            if event.message_id is not None:
                message_data = vk.messages.getById(message_ids=event.message_id)['items'][0]
                sender = vk.users.get(user_ids=event.user_id)[0]
                if event.from_chat and not event.from_me:  # Сообщение из беседы
                    chat_title = vk_session.method('messages.getChat', {'chat_id': event.chat_id})['title']
                    if "reply_message" in message_data:  # Ответ на сообщение
                        tg_session.send_message(data["tg_id"], f"*{chat_title}* | {get_reply(message_data)} | {sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
                    else:  # Обычный случай
                        tg_session.send_message(data["tg_id"], f"*{chat_title}* | {sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
                    logger.info(f"Message from VK chat '{chat_title}' forwarded to Telegram")
                if not event.from_me and event.from_user:  # Сообщение из лички
                    if "reply_message" in vk.messages.getById(message_ids=event.message_id)['items'][0]:
                        tg_session.send_message(data["tg_id"], f"{get_reply(message_data)} | {sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
                    else:
                        tg_session.send_message(data["tg_id"], f"{sender['first_name']} {sender['last_name']}: {event.message}", parse_mode='Markdown')
                    logger.info("Direct message from VK user forwarded to Telegram")
        except Exception as e:
            logger.error(f"Error in vk_work function: {e}")


Thread(target=vk_work).start()
Thread(target=tg_session.polling).start()
