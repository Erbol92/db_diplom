import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from models import *

from sqlalchemy.orm import sessionmaker
from sqlalchemy import or_
import pandas as pd

DSN = "postgresql://postgres:postgres@localhost:5432/translate_db"
engine = sq.create_engine(DSN)

drop_tables(engine)
create_tables(engine)

csv_files = ['enword.csv', 'ruword.csv']
for file in csv_files:
    df = pd.read_csv(file)
    df.to_sql(file.split('.')[0], con=engine, if_exists='append', index=False)
    print(f"Данные успешно загружены в таблицу `{file.split('.')[0]}`.")

# сессия
Session = sessionmaker(bind=engine)
session = Session()
print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = '8134749122:AAFLHf3GHejtlckk6HQneXKl8WfbF0AV4pI'
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()
    add_word = State()
    del_word = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        user = session.query(User).filter(User.tg_id == cid).first()
        if user is None:
            session.add(User(tg_id=cid))
            session.commit()
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.\n"
                         "У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого\n" "воспрользуйся инструментами:\n"
                         "добавить слово ➕,\n"
                         "удалить слово 🔙.\n"
                         "Ну что, начнём ⬇️")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    # получаем список слов общих + личные
    target_word = session.query(RuWord).\
        outerjoin(UserRuWords, UserRuWords.ruword_id == RuWord.id).\
        outerjoin(User, User.id == UserRuWords.user_id).\
        filter(or_(User.tg_id == cid, UserRuWords.user_id == None)).all()
    # получаем рандомное слово из списка
    target_word = target_word[random.randint(0, len(target_word)-1)]
    translate = target_word.true_translate  # брать из БД
    target_word_btn = types.KeyboardButton(target_word.title)
    # берем 3 рандомных слова на англ языке
    buttons.append(target_word_btn)
    others = session.query(EnWord).all()  # брать из БД
    random.shuffle(others)
    other_words_btns = [types.KeyboardButton(
        word.title) for word in others[:3]]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data.clear()
        data['target_word'] = target_word.title
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    bot.set_state(message.from_user.id, MyStates.del_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        print(data)
        word = data['target_word']
    cid = message.chat.id
    # получаем и проверяем есть ли это слово у пользователя
    words_to_del = session.query(RuWord)\
        .join(UserRuWords, RuWord.id == UserRuWords.ruword_id)\
        .join(User, User.id == UserRuWords.user_id)\
        .filter(RuWord.title == word, User.tg_id == cid).all()
    if words_to_del:
        session.query(UserRuWords).filter(
            UserRuWords.ruword_id == words_to_del[0].id).delete()
        session.commit()
        bot.send_message(message.chat.id, f'{word} удалено')
    else:
        bot.send_message(message.chat.id, 'Это не ваше слово')


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    bot.send_message(
        message.chat.id, 'введите слово на англ. и перевод через пробел')
    # меняем состояние
    bot.set_state(message.from_user.id, MyStates.add_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data.clear()
        data['add_word'] = 'add_word'


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data.get('target_word')
        state = data.get('add_word')
        print(target_word, state)
        if state == 'add_word':
            text = message.text.split(' ')
            hint = f'слово {text[0]}/{text[1]} добавлено'
            print(text)
            user = session.query(User).\
                filter(User.tg_id == message.chat.id).first()
            print(user)
            obj = RuWord(title=text[0], true_translate=text[1])
            print(obj)
            user.words.append(obj)
            session.add(user)
            session.commit()
            data['add_word'] = ''
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
