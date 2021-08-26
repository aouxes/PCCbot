import time
import config
import logging
import os
import pyautogui

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from obswebsocket import obsws, requests


# OBS-web-socket connect
ws = obsws('localhost', 4444, '12345')
ws.connect()

# log level
logging.basicConfig(level=logging.INFO)

# bot init
bot = Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# States
class Form(StatesGroup):
    authoriz = State()
    stream = State()
    replay_unload = State()
    replay_watch = State()
    replay_watching = State()
    replay_choose_player = State()
    moveto = State()


def auth(func):
    async def wrapper(message):
        for user_id in config.USERS_ID:
            if message.chat.id == user_id:
                return await func(message)
        return await message.answer('Вы не авторизованы.\nВведите /start для авторизации.')\
            and logging.info('Not auth ' + str(message.from_user))
    return wrapper


def admin(func):
    async def wrapper(message):
        for admin_id in config.ADMINS_ID:
            if message.chat.id == admin_id:
                return await func(message)
        return await message.answer('Это может только @aouxes.')\
            and logging.info('Not admin ' + str(message.from_user))
    return wrapper


async def screenshotting(delay, message):
    time.sleep(delay)
    pyautogui.screenshot('screenshot.png')
    await bot.send_photo(message.chat.id, photo=open('screenshot.png', 'rb'))


# welcome
@dp.message_handler(commands='start')
async def send_welcome(message: types.Message):
    logging.info('Starting ' + str(message.from_user))
    for user_id in config.USERS_ID:
        if message.chat.id == user_id:
            return await message.answer('Вы уже авторизованы.')
    await Form.authoriz.set()
    await message.answer('Привет! Я PC Controller Бот!\nВведите пароль, для авторизации.')


# Authorization
@dp.message_handler(state=Form.authoriz)
async def process_auth(message: types.Message, state: FSMContext):
    if message.text == config.PASSWORD:
        await state.finish()
        await message.answer('Пароль верный, успешная авторизация.\nДля доступа без авторизации напиши @aouxes.')
        logging.info('Success auth ' + str(message.from_user))
        config.USERS_ID.append(message.chat.id)
    else:
        await message.answer('Пароль не верный, попробуйте снова.')
        logging.info('UnSuccess auth ' + str(message.from_user))


# cancel state
@dp.message_handler(state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info('Cancelling state: ' + str(current_state) + ' ' + str(message.from_user))
    await state.finish()
    await message.answer('Отменено.')


# open Dota 2
@dp.message_handler(state='*', commands='dota')
@auth
async def dota(message: types.Message):
    logging.info('Dota 2 opening ' + str(message.from_user))
    await message.answer('Dota 2 запущена.')
    os.popen(r'C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\bin\win64\dota2.exe')
    await screenshotting(2, message)


# screenshot
@dp.message_handler(state='*', commands='screen')
@auth
async def screen(message: types.Message):
    logging.info('Screening ' + str(message.from_user))
    await screenshotting(0.2, message)


# Streaming
@dp.message_handler(state='*', commands='stream')
@auth
async def streaming(message: types.Message):
    logging.info('Streaming ' + str(message.from_user))
    markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_on = types.KeyboardButton(text='Включить')
    item_off = types.KeyboardButton(text='Выключить')
    markup_reply.add(item_on, item_off)
    await Form.stream.set()
    await message.answer('Что сделать со стримом?', reply_markup=markup_reply)


@dp.message_handler(state=Form.stream)
async def stream_control(message: types.Message, state: FSMContext):
    if message.text == 'Включить':
        logging.info('Stream on ' + str(message.from_user))
        ws.call(requests.StartStreaming())
        await message.answer('Трансляция включена.\nhttps://www.twitch.tv/asimeone13',
                             reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
    elif message.text == 'Выключить':
        logging.info('Stream off ' + str(message.from_user))
        ws.call(requests.StopStreaming())
        await message.answer('Трансляция выключена.', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()


# shutdown
@dp.message_handler(state='*', commands='shutdown')
@auth
@admin
async def shutdown(message: types.Message):
    logging.info('Shutdown ' + str(message.from_user))
    await message.answer('Завершение работы.')
    # os.system('shutdown -s')
    await screenshotting(1, message)


# watch replay dota 2
@dp.message_handler(state='*', commands='replay')
@auth
async def check_replay(message: types.Message):
    await Form.replay_unload.set()
    await message.answer('Введите ID матча.')


@dp.message_handler(state=Form.replay_unload)
async def replay_unload(message: types.Message):
    pyautogui.moveTo(550, 10)
    pyautogui.click()
    pyautogui.click()
    pyautogui.moveTo(900, 60)
    pyautogui.click()
    pyautogui.moveTo(1200, 60)
    pyautogui.click()
    pyautogui.typewrite(message.text)
    time.sleep(0.3)
    pyautogui.moveTo(1300, 60)
    pyautogui.click()
    await message.answer('Загружаю запись...')
    time.sleep(5)
    pyautogui.moveTo(1100, 650)
    pyautogui.click()
    markup_inline = types.InlineKeyboardMarkup(resize_keyboard=True)
    item_watch = types.KeyboardButton(text='Смотреть', callback_data='watch')
    markup_inline.add(item_watch)
    time.sleep(10)
    await bot.edit_message_text(text='Запись загружена!', chat_id=message.chat.id,
                                message_id=int(message.message_id)+1, reply_markup=markup_inline)
    await Form.replay_watch.set()


@dp.callback_query_handler(state=Form.replay_watch)
async def callback_watch(callback: types.CallbackQuery):
    if callback.data == 'watch':
        logging.info('Watching replay ' + str(callback.from_user))
        pyautogui.moveTo(1100, 650)
        pyautogui.click()
        markup_inline = types.InlineKeyboardMarkup(resize_keyboard=True)
        item_pause = types.KeyboardButton(text='Пауза', callback_data='pause')
        item_choose = types.KeyboardButton(text='Выбрать игрока', callback_data='choose')
        item_close = types.KeyboardButton(text='Закрыть', callback_data='close')
        markup_inline.add(item_pause, item_choose, item_close)
        await bot.edit_message_text(text='Реплей включен.\nНапиши /stream для управления трансляцией.',
                                    chat_id=callback.message.chat.id,
                                    message_id=callback.message.message_id,
                                    reply_markup=markup_inline)
        await Form.replay_watching.set()


@dp.callback_query_handler(state=Form.replay_watching)
async def replay_watching(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'pause':
        logging.info('Paused replay ' + str(callback.from_user))
        pyautogui.moveTo(960, 750)
        pyautogui.click()
        await callback.answer('Трансляция приостановлена/возобновлена')
    elif callback.data == 'choose':
        logging.info('Choosing player ' + str(callback.from_user))
        markup_inline = types.InlineKeyboardMarkup(resize_keyboard=True)
        item_one = types.KeyboardButton(text='1', callback_data='1')
        item_two = types.KeyboardButton(text='2', callback_data='2')
        item_three = types.KeyboardButton(text='3', callback_data='3')
        item_four = types.KeyboardButton(text='4', callback_data='4')
        item_five = types.KeyboardButton(text='5', callback_data='5')
        item_six = types.KeyboardButton(text='6', callback_data='6')
        item_seven = types.KeyboardButton(text='7', callback_data='7')
        item_eight = types.KeyboardButton(text='8', callback_data='8')
        item_nine = types.KeyboardButton(text='9', callback_data='9')
        item_ten = types.KeyboardButton(text='10', callback_data='10')
        markup_inline.add(item_one, item_two, item_three, item_four, item_five,
                          item_six, item_seven, item_eight, item_nine, item_ten)
        await bot.edit_message_text(text='Выбери игрока:',
                                    chat_id=callback.message.chat.id,
                                    message_id=callback.message.message_id,
                                    reply_markup=markup_inline)
        await Form.replay_choose_player.set()
    elif callback.data == 'close':
        logging.info('Closed replay ' + str(callback.from_user))
        pyautogui.moveTo(1340, 20)
        pyautogui.click()
        await bot.edit_message_text(text='Реплей закрыт.',
                                    chat_id=callback.message.chat.id,
                                    message_id=callback.message.message_id,
                                    reply_markup=types.InlineKeyboardMarkup(resize_keyboard=True))
        await state.finish()


async def choose_player(number, callback, x, y):
    markup_inline = types.InlineKeyboardMarkup(resize_keyboard=True)
    item_pause = types.KeyboardButton(text='Пауза', callback_data='pause')
    item_choose = types.KeyboardButton(text='Выбрать\nигрока', callback_data='choose')
    item_close = types.KeyboardButton(text='Закрыть', callback_data='close')
    markup_inline.add(item_pause, item_choose, item_close)
    if callback.data == str(number):
        pyautogui.moveTo(x, y)
        pyautogui.click()
        await Form.replay_watching.set()
        await bot.edit_message_text(text='Игрок выбран.', chat_id=callback.message.chat.id,
                                    message_id=callback.message.message_id,
                                    reply_markup=markup_inline)


@dp.callback_query_handler(state=Form.replay_choose_player)
async def replay_choose_player(callback: types.CallbackQuery):
    pyautogui.moveTo(1260, 60)
    pyautogui.click()
    pyautogui.moveTo(1260, 140)
    pyautogui.click()
    await choose_player(1, callback, 400, 15)
    await choose_player(2, callback, 450, 15)
    await choose_player(3, callback, 500, 15)
    await choose_player(4, callback, 550, 15)
    await choose_player(5, callback, 600, 15)
    await choose_player(6, callback, 770, 15)
    await choose_player(7, callback, 820, 15)
    await choose_player(8, callback, 870, 15)
    await choose_player(9, callback, 920, 15)
    await choose_player(10, callback, 970, 15)


# watch controller
@dp.message_handler(state='*', commands='watch')
@auth
async def watch_replay(message: types.Message):
    markup_inline = types.InlineKeyboardMarkup(resize_keyboard=True)
    item_pause = types.KeyboardButton(text='Пауза', callback_data='pause')
    item_choose = types.KeyboardButton(text='Выбрать игрока', callback_data='choose')
    item_close = types.KeyboardButton(text='Закрыть', callback_data='close')
    markup_inline.add(item_pause, item_choose, item_close)
    await message.answer('Управление реплеем:', reply_markup=markup_inline)
    await Form.replay_watching.set()


# left click
@dp.message_handler(state='*', commands='lclick')
@auth
async def left_click(message: types.Message):
    await message.answer('Нажал.')
    pyautogui.click()


# right click
@dp.message_handler(state='*', commands='rclick')
@auth
async def right_click(message: types.Message):
    await message.answer('Нажал.')
    pyautogui.click(button='right')


# double click
@dp.message_handler(state='*', commands='dclick')
@auth
async def double_click(message: types.Message):
    await message.answer('Нажал.')
    pyautogui.doubleClick()

# move to
@dp.message_handler(state='*', commands='moveto')
@auth
async def moveto(message: types.Message):
    await message.answer('Куда перенести курсор?')
    await Form.moveto.set()
    pyautogui.moveTo()


@dp.message_handler(state=Form.moveto)
async def moveto(message: types.Message, state: FSMContext):
    try:
        x, y = message.text.split()
        pyautogui.moveTo(int(x), int(y))
        await message.answer('Перенёс.')
    except ValueError:
        await message.answer('Некорректный ввод коордиант.')
    await state.finish()

# run long-polling
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
