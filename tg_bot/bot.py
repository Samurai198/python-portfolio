"""Telegram-бот для приёма заявок (салон, мастер, доставка, услуги).

Клиент нажимает «Оставить заявку», бот по шагам спрашивает имя,
телефон и услугу, а потом присылает готовую заявку владельцу бизнеса.

Настройка через переменные окружения:
    BOT_TOKEN  — токен от @BotFather
    ADMIN_ID   — ваш числовой Telegram ID (узнать можно у @userinfobot)

Запуск:
    python bot.py
"""

import asyncio
import os
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (KeyboardButton, Message, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove)

SERVICES = ["Стрижка", "Маникюр", "Консультация"]
PHONE_RE = re.compile(r"^\+?\d[\d\s()-]{9,}$")

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Оставить заявку")], [KeyboardButton(text="Цены и контакты")]],
    resize_keyboard=True,
)
services_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=s)] for s in SERVICES],
    resize_keyboard=True,
)
phone_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отправить мой номер", request_contact=True)]],
    resize_keyboard=True,
)


class Order(StatesGroup):
    name = State()
    phone = State()
    service = State()


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Здравствуйте! Я помогу записаться. Выберите действие:", reply_markup=main_kb)


@dp.message(F.text == "Цены и контакты")
async def prices(message: Message):
    await message.answer(
        "Стрижка — от 1000 ₽\nМаникюр — от 1500 ₽\nКонсультация — бесплатно\n\n"
        "Адрес: ул. Примерная, 1\nЕжедневно 10:00–20:00"
    )


@dp.message(F.text == "Оставить заявку")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(Order.name)
    await message.answer("Как вас зовут?", reply_markup=ReplyKeyboardRemove())


@dp.message(Order.name, F.text)
async def order_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(Order.phone)
    await message.answer("Ваш телефон? Можно нажать кнопку ниже.", reply_markup=phone_kb)


@dp.message(Order.phone)
async def order_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    if not PHONE_RE.match(phone):
        await message.answer("Похоже, номер с ошибкой. Пример: +7 900 123-45-67")
        return
    await state.update_data(phone=phone)
    await state.set_state(Order.service)
    await message.answer("Какая услуга нужна?", reply_markup=services_kb)


@dp.message(Order.service, F.text.in_(SERVICES))
async def order_service(message: Message, state: FSMContext, bot: Bot):
    data = await state.update_data(service=message.text)
    await state.clear()
    username = f"@{message.from_user.username}" if message.from_user.username else "без username"
    text = (f"🆕 Новая заявка\n\nИмя: {data['name']}\nТелефон: {data['phone']}\n"
            f"Услуга: {data['service']}\nTelegram: {username}")
    await bot.send_message(int(os.environ["ADMIN_ID"]), text)
    await message.answer("Спасибо! Мы перезвоним вам в ближайшее время.", reply_markup=main_kb)


@dp.message(Order.service)
async def order_service_wrong(message: Message):
    await message.answer("Выберите услугу кнопкой ниже 👇", reply_markup=services_kb)


async def main():
    bot = Bot(os.environ["BOT_TOKEN"])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
