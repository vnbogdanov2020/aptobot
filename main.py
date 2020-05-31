import urllib3
import emoji
from setting import bot_token
from setting import cnx
from setting import restlink, rest_all_link, chat_id_service
import telebot
from telebot import types
import requests
import json
import keyboards
import barcode




urllib3.disable_warnings()
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
    cursor.executemany("INSERT INTO user (user_id, first_name, last_name, phone_number) VALUES (%s,%s,%s,%s)",
                       (newdata,))
    cnx.commit()
    cursor.close()
    cnx.close()
    bot.send_message(message.chat.id, 'Привет, приятно познакомиться', reply_markup=keyboards.keyboard1)

#Обработка сообщений
@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text.lower() == 'товары':
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(text=u'\U0001F4CC'+' Мой список', callback_data='mylist:'),
            types.InlineKeyboardButton(text=u'\U0001F50D'+' Поиск', switch_inline_query_current_chat="")
                   )
        bot.send_message(message.chat.id, "Вы можете найти несколько товаров, добавить их в список, а затем найти в какой ближайшей аптеке этот список есть в наличии", reply_markup = markup)
    elif message.text.lower() == 'локация':
        bot.send_message(message.chat.id, 'Чтобы увидеть товар в ближайших аптеках, выберите город и обновите координаты', reply_markup=keyboards.keyboard2)
    elif message.text.lower() == 'назад':
        bot.send_message(message.chat.id, 'Главное меню', reply_markup=keyboards.keyboard1)
    elif message.text.lower() == 'город':
        try:
            response = requests.get(restlink+'/city/', verify=False)
            if response.status_code == 404:
                bot.send_message(message.chat.id, 'Не найден список городов')
            else:
                todos = json.loads(response.text)
                print(todos)

                markup = types.InlineKeyboardMarkup()
                for city in todos:
                    name = 'f'#city['city']
                    switch_button = types.InlineKeyboardButton(text=name, callback_data=name)
                    markup.add(switch_button)
                bot.send_message(message.chat.id, "Выберите ваш город", reply_markup=markup)
                #bot.send_message(message.chat.id, 'Главное меню', reply_markup=keyboards.keyboard1)

                #bot.send_message(message.chat.id, todos['name'] + chr(10) + chr(10) + 'Цена: ' + todos['price'] + ' тенге')
        except requests.exceptions.ConnectionError:
            bot.send_message(message.chat.id, 'Отсутствует связь с сервисом цен')
            #Оповестить сервис о проблемах
            bot.send_message(chat_id_service, 'Внимание! Проблема с доступом к сервису цен')

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
        try:
            response = requests.get(restlink+'/rest/' + bcode.decode(), verify=False)
            if response.status_code == 404:
                bot.send_message(message.chat.id, 'Не найдена цена на этот товар')
                # todos = json.loads(response.text)
            else:
                markup = types.InlineKeyboardMarkup()

                todos = json.loads(response.text)
                for row in todos['items']:
                    markup.add(
                        types.InlineKeyboardButton(text=u'\U0001F4CC', callback_data='prlist:' + str(row['nommodif'])),
                        types.InlineKeyboardButton(text=u'\U0001F30D', callback_data='local:' + str(row['nommodif'])),
                        types.InlineKeyboardButton(text=u'\U0001F50D', switch_inline_query_current_chat=""),
                    )
                    bot.send_message(message.chat.id,
                                     '*' + row['name'] + '* [.](' + row['burl'] + ') \n' + row['producer'],
                                     parse_mode='markdown',
                                     reply_markup=markup,
                                     )
        except requests.exceptions.ConnectionError:
            bot.send_message(message.chat.id, 'Отсутствует связь с сервисом цен')
            #Оповестить сервис о проблемах
            bot.send_message(chat_id_service, 'Внимание! Проблема с доступом к сервису цен')

@bot.inline_handler(func=lambda query: len(query.query) > 0)
def query_text(query):
        #print(query)
        response = requests.get(restlink +'/rest/' + query.query, verify=False)
        #if response.status_code == 404:
            # bot.send_message(message.chat.id, 'Ничего не найдено')
            # todos = json.loads(response.text)
        #else:
        todos = json.loads(response.text)

        results = []

        for row in todos['items']:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(text=u'\U0001F4CC', callback_data='prlist:' + str(row['nommodif'])),
                types.InlineKeyboardButton(text=u'\U0001F30D', callback_data='local:'+str(row['nommodif'])),
                types.InlineKeyboardButton(text=u'\U0001F50D', switch_inline_query_current_chat=""),
            )
            items = types.InlineQueryResultArticle(
                id=row['nommodif'], title=row['name'],
                description="Производитель: "+row['producer'],
                input_message_content=types.InputTextMessageContent(
                    message_text='*'+row['name']+'* [.](' + row['burl'] + ') \n'+row['producer'],
                    parse_mode='markdown',
                    disable_web_page_preview=False,
                     ),
                reply_markup=markup,
                thumb_url=row['murl'], thumb_width=100, thumb_height=100
            )
            results.append(items)
        bot.answer_inline_query(query.id, results)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        print(call)
        if call.data.find('mylist:') == 0:
            print('product_list')
            product_list = ''
            sql = ("SELECT product_id FROM user_product_list WHERE chat_id = %s")
            cursor.execute(sql, [(call.from_user.id)])
            products = cursor.fetchall()
            for product in products:
                product_list = product_list + product[0]
                print(product)
            bot.send_message(call.from_user.id, product_list)
            import_data('ЦВЕТНАЯ')
    # Если сообщение из инлайн-режима
    elif call.inline_message_id:
        if call.data.find('prlist:') == 0:
            cursor.executemany("INSERT INTO user_product_list (chat_id, product_id) VALUES (%s,%s)",
                               [(call.from_user.id,int(call.data.replace('prlist:',''))),])
            cnx.commit()
            cursor.close()
            cnx.close()
            bot.answer_callback_query(call.id, show_alert=True, text="Товар добавлен в список")


def import_data(company):
    if company=='ЦВЕТНАЯ':
        try:
            response = requests.get(rest_all_link, verify=False)
            if response.status_code == 404:
                bot.send_message(chat_id_service, 'Не оступен сервер ЦВЕТНАЯ')
            else:
                todos = json.loads(response.text)
                for row in todos['items']:
                    print(row['modif_name'])
        except requests.exceptions.ConnectionError:
            # Оповестить сервис о проблемах
            bot.send_message(chat_id_service, 'Внимание! Проблема с доступом к сервису цен')

bot.polling()