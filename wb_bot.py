import asyncio
import requests
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramAPIError
from db import register_user, get_user_token, init_db, save_token, reset_token
from wb_api import get_wb_feedbacks, send_answer_to_wb, check_token
from ai import generate_answer


logging.basicConfig(level=logging.INFO)


bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


#Хранилище отзывов для кнопок
pending_reviews = {}


class WaitToken(StatesGroup):
    wait_token = State()


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    if not reset_token(message.from_user.id):
        await message.answer("Ошибка сброса токена, попробуйте снова")
        return
    kb_start = [[
            types.KeyboardButton(text="🔑 Подключить токен")
        ],
        ]
    keyboard_start = types.ReplyKeyboardMarkup(keyboard=kb_start,resize_keyboard=True)
    await message.answer("Токен сброшен.", reply_markup=keyboard_start)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    register_user(message.from_user.id)
    token = get_user_token(message.from_user.id)
    if token:
        kb_start = [[
            types.KeyboardButton(text="🔑 Заменить токен"),
            types.KeyboardButton(text="📝 Ответить на отзывы")
        ],
        ]
        keyboard_start = types.ReplyKeyboardMarkup(keyboard=kb_start,resize_keyboard=True)
        
        await message.answer("Добро пожаловать обратно!\n\n" "Маяк Селлеров - бот для ответов на отзывы", reply_markup=keyboard_start)
        
        await message.answer("🟢 Токен подключен")
    else:
        kb_start = [[
            types.KeyboardButton(text="🔑 Подключить токен")
        ],
        ]
        keyboard_start = types.ReplyKeyboardMarkup(keyboard=kb_start,resize_keyboard=True)
        await message.answer("Добро пожаловать новый пользователь!\n\n" "Маяк Селлеров - бот для ответов на отзывы", reply_markup=keyboard_start)
        await message.answer("🔴 Токен не подключен")


#Ввод токена ВБ
@dp.message(StateFilter(None), Command("token"))
async def cmd_token(message: Message, state: FSMContext):
    await message.answer(
        text="Введите токен:",
    )
    await state.set_state(WaitToken.wait_token)

@dp.message(WaitToken.wait_token)
async def insert_token(message: Message, state: FSMContext):
    await message.answer("⌛ Проверка токена...")
    token = message.text.strip()
    await state.clear()
    token_status = check_token(token)
    if not token_status:
        await message.answer("Непредвиденная ошибка, перезапустите команду /token")
        return
    if token_status == 200:
        await message.answer("✅🔑 Токен успешно подтвержден!")
        kb_start = [[
            types.KeyboardButton(text="🔑 Заменить токен"),
            types.KeyboardButton(text="📝 Ответить на отзывы")
        ],
        ]
        keyboard_start = types.ReplyKeyboardMarkup(keyboard=kb_start,resize_keyboard=True)
        
        await message.answer("🟢 Токен подключен", reply_markup=keyboard_start)
        if not save_token(message.from_user.id, token):
            await message.answer("Непредвиденная ошибка, перезапустите команду /token")
            return
        return
    elif token_status == 401:
        await message.answer("❌🔑 Неверный токен или не авторизован!")
        return
    elif token_status == 429:
        await message.answer("❌ Слишком много запросов!")
        return
    else:
        await message.answer("❌ Другая ошибка токена!")
        return

@dp.message(F.text == "🔑 Подключить токен")
async def start_token_connect(message: types.Message, state: FSMContext):
    await cmd_token(message, state)

@dp.message(F.text == "🔑 Заменить токен")
async def start_token_replace(message: types.Message, state: FSMContext):
    await cmd_token(message, state)


@dp.message(Command("reviews"))
async def cmd_reviews(message: types.Message):
    await message.answer("⌛ Загружаю ответы с WB...")
    token = get_user_token(message.from_user.id)
    if not token:
        await message.answer("Токен отсутствует, попробуйте сначала ввести токен: /token")
        return
    feedbacks = get_wb_feedbacks(token)
    #Вот тут надо разобраться с ошибкой получения отзывов, сейчас просто проверяю на None, но может быть и другой формат ответа при ошибке
    if not feedbacks:
        await message.answer(f"❌ Ошибка загрузки ответов с WB")
        return
    if not feedbacks:
        await message.answer("✅ Нет неотвеченных отзывов!")
        return
    
    await message.answer(f"Найдено отзывов: {len(feedbacks)}. Генерируем ответы...")

    for fb in feedbacks:
        answer = generate_answer(fb)
        if not answer:
            await message.answer(f"Неудалось обработать отзыв {fb['id']}\n\n Переходим к следующему отзыву...")
            continue

        #Сохраняем для кнопок
        pending_reviews[fb["id"]] = {
            "answer": answer,
            "feedback_id": fb["id"]
        }

        #Формируем текст ВОТ ЗДЕСЬ ЕСТЬ ПРОБЛЕМА, НУЖНО СОЕДИНИТЬ PROS TEXT и ЕЩЕ
        review_text = f"{fb.get("text")} {fb.get("pros")} {fb.get("cons")}"
        start = "⭐" * fb["productValuation"]
        product = fb["productDetails"]["productName"]

        text = (
            f"👤 {fb['userName']} | {start}\n"
            f"📦 {product}\n\n"
            f"💭 Отзыв: \n{review_text}\n\n"
            f"✍️ Ответ: \n{answer}"
        )


        #Кнопки
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(
                text="✅ Отправить",
                callback_data=f"send_{fb['id']}"
            ),
            types.InlineKeyboardButton(
                text="⏭️ Пропустить",
                callback_data=f"skip_{fb['id']}"
            )
        )
        try:
            await message.answer(text, reply_markup=builder.as_markup())
        except TelegramAPIError:
            await message.answer(f"Ошибка при формировании отзыва...\n\n Переходим к следующему отзыву!")
            del pending_reviews[fb["id"]]
            continue

@dp.message(F.text == "📝 Ответить на отзывы")
async def reply_reviews(message: types.Message):
    await cmd_reviews(message)
        
@dp.callback_query(F.data.startswith("send_"))
async def on_send(callback: types.CallbackQuery):
    feedback_id = callback.data.replace("send_", "")
    review = pending_reviews.get(feedback_id)

    if not review:
        await callback.answer("Отзыв не найден")
        return
    try:
        token = get_user_token(callback.from_user.id)
        success = send_answer_to_wb(feedback_id, review["answer"], token)
    except requests.exceptions.RequestException:
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ ОШИБКА API"
        )
        del pending_reviews[feedback_id]
        await callback.answer()
        return
    if success:
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ ОТПРАВЛЕНО"
        )
    else:
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ ОШИБКА ОТПРАВКИ"
        )

    del pending_reviews[feedback_id]
    await callback.answer()

@dp.callback_query(F.data.startswith("skip_"))
async def on_skip(callback: types.CallbackQuery):
    feedback_id = callback.data.replace("skip_", "")
    pending_reviews.pop(feedback_id, None)

    await callback.message.edit_text(
        callback.message.text + "\n\n⏭️ ПРОПУЩЕНО"
    )
    await callback.answer()
    
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())