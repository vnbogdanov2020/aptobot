# -*- coding: utf-8 -*-
"""
Created on Sun May  3 23:09:41 2020

@author: User
"""
import telebot
from telebot import types

keyboard1 = telebot.types.ReplyKeyboardMarkup(resize_keyboard=1)
keyboard1.row('Поиск товара','Локация')


keyboard2 = telebot.types.ReplyKeyboardMarkup(resize_keyboard=1)
key1 = types.KeyboardButton(text='Город')
key2 = types.KeyboardButton(text='Координаты',request_location=True)
keyboard2.add(key1,key2)
key3 = types.KeyboardButton(text='Назад')
keyboard2.add(key3)
#keyboard1.row('Привет', 'Пока','Я тебя люблю')
#keyboard1.row('Запрос')

NewUser = telebot.types.ReplyKeyboardMarkup(resize_keyboard=1)
key_b = types.KeyboardButton(text='Отправить контакт',request_contact=True)
NewUser.add(key_b)

