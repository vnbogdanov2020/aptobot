import urllib3
from setting import bot_token
from setting import cnx
from setting import restlink, rest_all_link, chat_id_service, rest_link_product, rest_link_store, rest_link_stock
import telebot
from telebot import types
import requests
import json
import keyboards
import barcode
import time
from service import transliterate

urllib3.disable_warnings()
cursor = cnx.cursor(buffered=True)
cursor_search = cnx.cursor(buffered=True)
cursor_search.execute("SET SESSION MAX_EXECUTION_TIME=10000")

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
    #cursor.close()
    #cnx.close()
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
        if message.chat.id == chat_id_service:
            markup.add(
                types.InlineKeyboardButton(text='Обновить данные', callback_data='refresh:'))
        bot.send_message(message.chat.id, "КАК ЭТО РАБОТАЕТ:\n"
                                          "1. Выберите ваш город в пункте ЛОКАЦИЯ\n"
                                          "2. Уточните ваши координаты в пункте ЛОКАЦИЯ\n"
                                          "3. Найдите один или несколько товаров и добавьте их в список\n"
                                          "4. Бот найдет ближайшие к вам аптеки в которых есть товар из списка", parse_mode='HTML', reply_markup = markup)
    elif message.text.lower() == 'локация':
        usercity = get_user_city(message.chat.id)
        citykeyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=1)
        citykeyboard.add(types.KeyboardButton(text='Выбрать город ('+usercity+')'),
                         types.KeyboardButton(text='Обновить координаты', request_location=True))
        citykeyboard.add(types.KeyboardButton(text='Назад'))
        bot.send_message(message.chat.id, 'Чтобы увидеть товар в ближайших аптеках, выберите город и обновите координаты', reply_markup=citykeyboard)
    elif message.text.lower() == 'назад':
        bot.send_message(message.chat.id, 'Главное меню', reply_markup=keyboards.keyboard1)
    elif message.text.lower().find('выбрать город') == 0:
        try:
            cursor.execute('select city from store s group by city order by city')
            citys = cursor.fetchall()
            markup = types.InlineKeyboardMarkup()
            for city in citys:
                name = city[0]
                switch_button = types.InlineKeyboardButton(text=name, callback_data='mycity:'+name)
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
    #cursor.close()
    #cnx.close()
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

@bot.inline_handler(func=lambda query: len(query.query) >= 2)
def query_text(query):

        offset = int(query.offset) if query.offset else 0
        try:
            #cursor_search.execute('SELECT nommodif, name, producer, photo, "+" city, "-" price FROM product WHERE lower(concat(name,producer,barcode,COALESCE(search_key,""))) LIKE lower(%s) LIMIT 5 OFFSET %s', ('%'+query.query+'%',offset,))

            usercity = get_user_city(query.from_user.id)


            SQL = """\
                    select t.nommodif, t.name, t.producer, t.photo, t.city, case when %s='' then 0 ELSE t.price end price
                    FROM (SELECT p1.nommodif, p1.name, p1.producer, p1.photo, p3.city, p2.price FROM product p1
                    inner join stock p2 on p2.company = p1.company and p2.product_id = p1.nommodif
                    inner join store p3 on p3.company = p2.company and p3.name = p2.store
                    WHERE lower(concat(p1.name,COALESCE(p1.search_key,''))) LIKE lower(%s)
                    group by p1.nommodif, p1.name, p1.producer, p1.photo, p3.city, p2.price) t
                    WHERE (t.city = %s or %s='') LIMIT 20 OFFSET %s
                    """
            cursor_search.execute(SQL, (usercity,'%'+query.query+'%',usercity,usercity,offset,))

            products = cursor_search.fetchall()

            results = []
            try:
                m_next_offset = str(offset + 20) if len(products) == 20 else None
                for product in products:
                    try:
                        markup = types.InlineKeyboardMarkup()
                        markup.add(
                            types.InlineKeyboardButton(text=u'\U0001F4CC', callback_data='prlist:' + str(product[0])),
                            types.InlineKeyboardButton(text=u'\U0001F30D', callback_data='local:'+str(product[0])),
                            types.InlineKeyboardButton(text=u'\U0001F50D', switch_inline_query_current_chat=""),
                        )
                        items = types.InlineQueryResultArticle(
                            id=product[0], title=product[1],
                            description="Производитель: "+product[2]+"\nЦена: "+str(product[5])+" тенге",
                            input_message_content=types.InputTextMessageContent(
                                message_text='*'+product[1]+'* [.](' + product[3] + ') \n'+product[2],
                                parse_mode='markdown',
                                disable_web_page_preview=False,
                                 ),
                            reply_markup=markup,
                            thumb_url=product[3], thumb_width=100, thumb_height=100
                        )
                        results.append(items)
                    except Exception as e:
                        print(e)
                bot.answer_inline_query(query.id, results, next_offset=m_next_offset if m_next_offset else "", cache_time=86400)
            except Exception as e:
                print(e)
        except Exception as e:
            print(e)

def get_user_city(in_user_id):
    # Ищем город пользователя
    try:
        sql = ("SELECT city FROM user WHERE user_id = %s")
        cursor.execute(sql, [(in_user_id)])
        city = cursor.fetchone()
        if city:
            return city[0]
        else:
            return ''
    except Exception as e:
        print(e)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        #print(call)
        if call.data.find('mycity:') == 0:
            cursor.execute('UPDATE user SET city = %s WHERE user_id = %s', (call.data.replace('mycity:',''),call.from_user.id))
            cnx.commit()
            #cursor.close()
            #cnx.close()
            usercity = call.data.replace('mycity:','')
            citykeyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=1)
            citykeyboard.add(types.KeyboardButton(text='Выбрать город ('+usercity+')'),
                             types.KeyboardButton(text='Обновить координаты', request_location=True))
            citykeyboard.add(types.KeyboardButton(text='Назад'))

            bot.send_message(call.from_user.id,
                             'Ваш город: '+usercity,
                             reply_markup=citykeyboard)
        if call.data.find('mylist:') == 0:
            try:
                product_list = 'СПИСОК ДЛЯ ПОИСКА:\n\n'
                sql = ("SELECT p2.name, p2.producer FROM user_product_list p1, product p2 WHERE p2.nommodif = p1.product_id AND p1.chat_id = %s group by p2.name, p2.producer order by p2.name")
                cursor.execute(sql, [(call.from_user.id)])
                products = cursor.fetchall()
                for product in products:
                    product_list = product_list + '*'+product[0]+'*'+'\n'+product[1]+'\n'+'\n'

                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(text=u'\U0001F5D1 Очистить', callback_data='clearlist:'),
                    types.InlineKeyboardButton(text=u'\U0001F30D Рядом', callback_data='locallist:'),
                )
                bot.send_message(call.from_user.id,
                                 product_list,
                                 parse_mode='markdown',
                                 reply_markup=markup,)
            except Exception as e:
                print(e)
                bot.send_message(call.from_user.id,
                                 'Список пустой...')
        if call.data.find('clearlist:') == 0:
            #Очистка списка пользоателя
            cursor.execute('DELETE FROM user_product_list WHERE chat_id = %s', [(call.from_user.id)])
            cnx.commit()
            bot.send_message(call.from_user.id,
                             'Ваш список товаров удален.')
        if call.data.find('refresh:') == 0:
            #Импорт данных из аптек
            #import_product()
            #import_store()
            import_stock()
    # Если сообщение из инлайн-режима
    elif call.inline_message_id:
        if call.data.find('prlist:') == 0:
            cursor.executemany("INSERT INTO user_product_list (chat_id, product_id) VALUES (%s,%s)",
                               [(call.from_user.id,call.data.replace('prlist:','')),])
            cnx.commit()
            #cursor.close()
            #cnx.close()
            bot.answer_callback_query(call.id, show_alert=True, text="Товар добавлен в список")


def import_product():
    #Импорт справочника товаров
    try:
        response = requests.get(rest_link_product, verify=False)
        if response.status_code == 404:
            bot.send_message(chat_id_service, 'Не оступен сервер ЦВЕТНАЯ')
        else:
            todos = json.loads(response.text)
            indata = []

            cursor.execute("DELETE FROM product WHERE company='ЦВЕТНАЯ'")

            for row in todos['items']:
                indata.append((
                        'ЦВЕТНАЯ',
                        row['nommodif'],
                        row['modif_name'],
                        row['producer'],
                        row['barcode'],
                        row['photo'],
                        row['skey'],
                ))

            '''
            try:
                while todos['next']['$ref']:
                    newlink = todos['next']['$ref']
                    print(newlink)
                    response = requests.get(newlink, verify=False)
                    todos = json.loads(response.text)
                    for row in todos['items']:
                        indata.append((
                            'ЦВЕТНАЯ',
                            row['nommodif'],
                            row['modif_name'],
                            row['producer'],
                            row['barcode']
                        ))
            '''
            cursor.executemany("INSERT INTO product (company,nommodif,name,producer,barcode,photo,search_key) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                               indata)
            cnx.commit()
            bot.send_message(chat_id_service, 'Справочник товаров обновлен')
            #cursor.close()
            #cnx.close()
    except requests.exceptions.ConnectionError:
        # Оповестить сервис о проблемах
        bot.send_message(chat_id_service, 'Внимание! Проблема с доступом к сервису цен')

def import_store():
    #Импорт справочника аптек
    try:
        response = requests.get(rest_link_store, verify=False)
        if response.status_code == 404:
            bot.send_message(chat_id_service, 'Не доступен сервер ЦВЕТНАЯ')
        else:
            todos = json.loads(response.text)
            indata = []

            cursor.execute("DELETE FROM store WHERE company='ЦВЕТНАЯ'")

            for row in todos['items']:
                indata.append((
                    row['company'],
                    row['store'],
                    row['city'],
                    row['address'],
                    row['lon'],
                    row['lat'],
                    row['phone'],
                    row['resh']
                ))
            cursor.executemany(
                "INSERT INTO store (company,name,city,address,longitude,latitude,phone,mode) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                indata)
            cnx.commit()
            bot.send_message(chat_id_service, 'Справочник аптек обновлен')
            #cursor.close()
            #cnx.close()
    except requests.exceptions.ConnectionError:
        # Оповестить сервис о проблемах
        bot.send_message(chat_id_service, 'Внимание! Проблема с доступом к сервису цен')

def import_stock():
    #Импорт остатков
    try:
        response = requests.get(rest_link_stock, verify=False)
        if response.status_code == 404:
            bot.send_message(chat_id_service, 'Не оступен сервер ЦВЕТНАЯ')
        else:
            todos = json.loads(response.text)
            indata = []

            cursor.execute("DELETE FROM stock WHERE company='ЦВЕТНАЯ'")

            for row in todos['items']:
                indata.append((
                        'ЦВЕТНАЯ',
                        row['store'],
                        row['nommodif'],
                        row['restfact'],
                        row['price']
                ))
            try:
                while todos['next']['$ref']:
                    newlink = todos['next']['$ref']
                    print(newlink)
                    response = requests.get(newlink, verify=False)
                    todos = json.loads(response.text)
                    for row in todos['items']:
                        indata.append((
                            'ЦВЕТНАЯ',
                            row['store'],
                            row['nommodif'],
                            row['restfact'],
                            row['price']
                        ))
            except Exception as e:
                print(e)
            cursor.executemany("INSERT INTO stock (company,store,product_id,qnt,price) VALUES (%s,%s,%s,%s,%s)",
                               indata)
            cnx.commit()
            bot.send_message(chat_id_service, 'Остатки обновлены')
            #cursor.close()
            #cnx.close()
    except requests.exceptions.ConnectionError:
        # Оповестить сервис о проблемах
        bot.send_message(chat_id_service, 'Внимание! Проблема с доступом к сервису цен')

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)
        # повторяем через 15 секунд в случае недоступности сервера Telegram
        time.sleep(15)