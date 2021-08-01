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
    replay_choose_player = State()


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


def screenshoting(delay):
    time.sleep(delay)
    pyautogui.screenshot('screenshot.png')


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
    screenshoting(2)
    await bot.send_photo(message.chat.id, photo=open('screenshot.png', 'rb'))


# screenshot
@dp.message_handler(state='*', commands='screen')
@auth
async def screen(message: types.Message):
    logging.info('Screening ' + str(message.from_user))
    screenshoting(0.2)
    await bot.send_photo(message.chat.id, photo=open('screenshot.png', 'rb'))


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
    screenshoting(1)
    await bot.send_photo(message.chat.id, photo=open('screenshot.png', 'rb'))


# watch replay dota 2
@dp.message_handler(state='*', commands='replay')
@auth
async def check_replay(message: types.Message):
    await Form.replay_unload.set()
    await message.answer('Введите ID матча.')


@dp.message_handler(state=Form.replay_unload)
async def replay_unload(message: types.Message, state: FSMContext):
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
    time.sleep(4)
    pyautogui.moveTo(1100, 650)
    pyautogui.click()
    markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_watch = types.KeyboardButton(text='Смотреть')
    markup_reply.add(item_watch)
    screenshoting(1)
    await message.answer('Загружаю запись... \nНажми "Смотреть" через 5-10 секунд.',
                         reply_markup=markup_reply)
    await bot.send_photo(message.chat.id, photo=open('screenshot.png', 'rb'))
    await Form.replay_watch.set()


@dp.message_handler(state=Form.replay_watch)
async def replay_watch(message: types.Message, state: FSMContext):
    if message.text == 'Смотреть':
        logging.info('Watching replay ' + str(message.from_user))
        pyautogui.moveTo(1100, 650)
        pyautogui.click()
        markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_pause = types.KeyboardButton(text='Пауза')
        item_choose = types.KeyboardButton(text='Выбрать игрока')
        item_close = types.KeyboardButton(text='Закрыть')
        markup_reply.add(item_pause, item_choose, item_close)
        await message.answer('Реплей включен. Напиши /stream для управления трансляцией',
                             reply_markup=markup_reply)
        screenshoting(3)
        await bot.send_photo(message.chat.id, photo=open('screenshot.png', 'rb'))
    elif message.text == 'Пауза':
        logging.info('Paused replay ' + str(message.from_user))
        pyautogui.moveTo(960, 750)
        pyautogui.click()
        await message.answer('Трансляция приостановлена/возобновлена')
    elif message.text == 'Выбрать игрока':
        logging.info('Choosing player ' + str(message.from_user))
        markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_one = types.KeyboardButton(text='1')
        item_two = types.KeyboardButton(text='2')
        item_three = types.KeyboardButton(text='3')
        item_four = types.KeyboardButton(text='4')
        item_five = types.KeyboardButton(text='5')
        item_six = types.KeyboardButton(text='6')
        item_seven = types.KeyboardButton(text='7')
        item_eight = types.KeyboardButton(text='8')
        item_nine = types.KeyboardButton(text='9')
        item_ten = types.KeyboardButton(text='10')
        markup_reply.add(item_one, item_two, item_three, item_four, item_five,
                         item_six, item_seven, item_eight, item_nine, item_ten)
        await message.answer('Выбери игрока.', reply_markup=markup_reply)
        await Form.replay_choose_player.set()
    elif message.text == 'Закрыть':
        logging.info('Closed replay ' + str(message.from_user))
        pyautogui.moveTo(1340, 20)
        pyautogui.click()
        await message.answer('Реплей закрыт.', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()


@dp.message_handler(state=Form.replay_choose_player)
async def replay_choose_player(message: types.Message, state: FSMContext):
    markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_pause = types.KeyboardButton(text='Пауза')
    item_choose = types.KeyboardButton(text='Выбрать игрока')
    item_close = types.KeyboardButton(text='Закрыть')
    markup_reply.add(item_pause, item_choose, item_close)
    if message.text == '1':
        pyautogui.moveTo(400, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '2':
        pyautogui.moveTo(450, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '3':
        pyautogui.moveTo(500, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '4':
        pyautogui.moveTo(550, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '5':
        pyautogui.moveTo(600, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '6':
        pyautogui.moveTo(770, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '7':
        pyautogui.moveTo(820, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '8':
        pyautogui.moveTo(870, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '9':
        pyautogui.moveTo(920, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)
    elif message.text == '10':
        pyautogui.moveTo(970, 15)
        pyautogui.click()
        await Form.replay_watch.set()
        await message.answer('Игрок выбран.', reply_markup=markup_reply)


# run long-polling
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
