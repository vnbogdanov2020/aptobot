
from setting import bot_token
from setting import cnx
from setting import restlink
from setting import chat_id_service
import telebot
from telebot import types
import requests
import json
import keyboards
import barcode


cursor = cnx.cursor()

bot = telebot.TeleBot(bot_token)

#Первый запуск
@bot.message_handler(commands=['start'])
def start_message(message):
    sql = ("SELECT * FROM user WHERE user_id= %s")
    cursor.execute(sql, [(message.from_user.id)])
    user = cursor.fetchone()
    if not user:
        bot.send_message(message.chat.id, 'Привет, я тебя не знаю ', reply_markup=keyboards.NewUser)
    else:
        bot.send_message(message.chat.id, 'С возвращением!', reply_markup=keyboards.keyboard1)

#Регистрация пользователя
@bot.message_handler(content_types=['contact'])
def add_user(message):
    #conn = sqlite3.connect(bot_db)
    #cursor = conn.cursor()
    newdata = (message.contact.user_id,
               message.contact.first_name,
               message.contact.last_name,
               message.contact.phone_number
               )
    cursor.executemany("INSERT INTO user (user_id, first_name, last_name, phone_number) VALUES (%s,%s,%s,%s)", (newdata,))
    cnx.commit()
    cursor.close()
    cnx.close()
    bot.send_message(message.chat.id, 'Привет, приятно познакомиться', reply_markup=keyboards.keyboard1)

#Обработка сообщений
@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text.lower() == 'узнать цену':
        bot.send_message(message.chat.id, "Напишите название или отправьте фото штрихкода товара и я скажу сколько он стоит")
    elif message.text.lower() == 'место':
        bot.send_message(message.chat.id, 'Чтобы увидеть товар в ближайших аптеках, выберите город и обновите координаты', reply_markup=keyboards.keyboard2)
    elif message.text.lower() == 'назад':
        bot.send_message(message.chat.id, 'Главное меню', reply_markup=keyboards.keyboard1)

#Регистрация местоположения
@bot.message_handler(content_types=['location'])
def send_location(message):
    print(message)
    newdata = (
               message.location.latitude,
               message.location.longitude,
               message.from_user.id
               )
    cursor.executemany("UPDATE user SET latitude = %s, longitude = %s WHERE user_id = %s",
                       (newdata,))
    cnx.commit()
    cursor.close()
    cnx.close()
    bot.send_message(message.chat.id, 'Ваши координаты обновлены')

#Получение фото товара
@bot.message_handler(content_types=['photo'])
def sent_barcode(message):
    raw = message.photo[2].file_id
    file_info = bot.get_file(raw)
    downloaded_file = 'https://api.telegram.org/file/bot' + bot_token + '/' + file_info.file_path
    bcode = barcode.read_barcode(downloaded_file,message.chat.id)
    print(str(bcode))

    if bcode == 'No':
        bot.send_message(message.chat.id, 'Не удалось распознать код. Попробуйте еще раз')
    else:
        # print('http://172.16.0.27/ords/apex_cvt/aptobot/rest/'+bcode.decode())
        print(typr(bcode))
        try:
            response = requests.get(restlink + bcode.decode(), verify=False)
            if response.status_code == 404:
                bot.send_message(message.chat.id, 'Не найдена цена на этот товар')
                # todos = json.loads(response.text)
            else:
                todos = json.loads(response.text)
                bot.send_message(message.chat.id, todos['name'] + chr(10) + chr(10) + 'Цена: ' + todos['price'] + ' тенге')
        except requests.exceptions.ConnectionError:
            bot.send_message(message.chat.id, 'Отсутствует связь с сервисом цен')
            #Оповестить сервис о проблемах
            bot.send_message(chat_id_service, 'Внимание! Проблема с доступом к сервису цен')

bot.polling()