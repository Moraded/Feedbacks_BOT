import asyncio
import requests
import os
import logging
from dotenv import load_dotenv
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

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


#Хранилище отзывов для кнопок
pending_reviews = {}

#Хранилище отзывов для режима ответов
user_feedbacks = {}

#Индекс для отслеживания текущего отзыва в ручном режиме
user_review_index = {}


class WaitToken(StatesGroup):
    wait_token = State()

#Клавиатуры
def answermod_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="✍️ Ручной режим", callback_data="reply_manual")],
        [types.InlineKeyboardButton(text="🤖 Ответить на все", callback_data="reply_auto")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def default_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="🔑 Заменить токен", callback_data="token_replace")],
        [types.InlineKeyboardButton(text="🔄 Сбросить токен", callback_data="token_reset")],
        [types.InlineKeyboardButton(text="🔎 Проверить наличие отзывов", callback_data="check_update")],
        [types.InlineKeyboardButton(text="📝 Ответить на отзывы", callback_data="reviews")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def connect_token_keyboard():
    buttons = [
        [
            types.InlineKeyboardButton(text="➡️🔑 Подключить токен", callback_data="token_connect"),

        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    if not reset_token(message.from_user.id):
        await message.answer("❌ Ошибка сброса токена, попробуйте снова")
        return
    await message.answer("✅ Токен сброшен", reply_markup=connect_token_keyboard())


@dp.callback_query(F.data == "token_reset")
async def callback_token_reset(callback: types.CallbackQuery):
    if not reset_token(callback.from_user.id):
        await callback.message.edit_text("❌ Ошибка сброса токена, попробуйте снова")
        return
    await callback.message.edit_text("✅ Токен сброшен", reply_markup=connect_token_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "callback_start")
async def cmd_start(callback: types.CallbackQuery):
    register_user(callback.from_user.id)
    token = get_user_token(callback.from_user.id)
    if token:
        await callback.message.edit_text(
            "* Готовы продолжить работу?\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Статус токена: ✅ Подключен", reply_markup=default_keyboard()
            )
    else:
        await callback.message.edit_text(
            "* Для того, чтобы использовать бота, необходимо подключить API токен кабинета. Достаточно создать новый токен в кабинете WB с доступом к категории 'вопросы и отзывы (чтение и запись)'\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Бот через API токен кабинета получает данные о отзывах, обрабатывает и генерирует ответы.\n\n"
            "* Статус токена: ❌ Не подключен", reply_markup=connect_token_keyboard()
            )



@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    register_user(message.from_user.id)
    token = get_user_token(message.from_user.id)
    if token:
        await message.answer(
            "* Готовы продолжить работу?\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Статус токена: ✅ Подключен", reply_markup=default_keyboard()
            )
    else:
        await message.answer(
            "* Для того, чтобы использовать бота, необходимо подключить API токен кабинета. Достаточно создать новый токен в кабинете WB с доступом к категории 'вопросы и отзывы (чтение и запись)'\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Бот через API токен кабинета получает данные о отзывах, обрабатывает и генерирует ответы.\n\n"
            "* Статус токена: ❌ Не подключен", reply_markup=connect_token_keyboard()
            )


@dp.callback_query(F.data == "check_update")
async def callback_check_update(callback: types.CallbackQuery):
    await callback.message.edit_text("⌛ Сканирую отзывы с WB...")
    token = get_user_token(callback.from_user.id)
    if not token:
        await callback.message.edit_text("Токен отсутствует, попробуйте сначала ввести токен: /token")
        return
    feedbacks = get_wb_feedbacks(token)
    #Проверка на ошибки загрузки
    if feedbacks is None:
        await callback.message.edit_text(f"❌ Ошибка загрузки ответов с WB")
        return
    if not feedbacks:
        await callback.message.edit_text("✅ Нет неотвеченных отзывов!")
        return
    
    user_feedbacks[callback.from_user.id] = feedbacks

    await callback.message.edit_text(f"У вас есть новые отзывы! 📊 Найдено отзывов: {len(feedbacks)}", reply_markup=default_keyboard())



#Ввод токена ВБ
@dp.message(StateFilter(None), Command("token"))
async def cmd_token(message: Message, state: FSMContext):
    await message.answer(
        text="🔑 Введите токен:",
    )
    await state.set_state(WaitToken.wait_token)

@dp.message(WaitToken.wait_token)
async def insert_token(message: Message, state: FSMContext):
    data = await state.get_data()
    status_msg = await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=data.get("message_id"),
        text="⌛ Проверяю токен..."
    )
    token = message.text.strip()
    await message.delete()
    await state.clear()
    token_status = check_token(token)
    if not token_status:
        await message.answer("❌ Непредвиденная ошибка при проверке токена, попробуйте снова")
        return
    if token_status == 200:
        await status_msg.edit_text("✅🔑 Токен успешно подтвержден!", reply_markup=default_keyboard())
        if not save_token(message.from_user.id, token):
            await message.answer("❌ Непредвиденная ошибка, попробуйте снова", reply_markup=default_keyboard())
            return
        return
    elif token_status == 401:
        await status_msg.edit_text("❌🔑 Неверный токен или не авторизован!", reply_markup=default_keyboard())
        return
    elif token_status == 429:
        await status_msg.edit_text("❌ 🕒 Слишком много запросов!", reply_markup=default_keyboard())
        return
    else:
        await status_msg.edit_text("❌ Другая ошибка токена!", reply_markup=default_keyboard())
        return

@dp.callback_query(F.data == "token_connect")
async def start_token_connect(callback: types.CallbackQuery, state: FSMContext):
    msg = await callback.message.edit_text("🔑 Введите токен:")
    await state.update_data(message_id=msg.message_id)
    await state.set_state(WaitToken.wait_token)
    await callback.answer()


@dp.callback_query(F.data == "token_replace")
async def start_token_replace(callback: types.CallbackQuery, state: FSMContext):
    msg = await callback.message.edit_text("🔑 Введите новый токен:")
    await state.update_data(message_id=msg.message_id)
    await state.set_state(WaitToken.wait_token)
    await callback.answer()


@dp.callback_query(F.data == "reviews")
async def callback_reviews(callback: types.CallbackQuery):
    await callback.message.edit_text("⌛ Загружаю отзывы с WB...")
    token = get_user_token(callback.from_user.id)
    if not token:
        await callback.message.edit_text("Токен отсутствует, попробуйте сначала ввести токен: /token")
        return
    feedbacks = get_wb_feedbacks(token)
    #Проверка на ошибки загрузки
    if feedbacks is None:
        await callback.message.edit_text(f"❌ Ошибка загрузки ответов с WB")
        return
    if not feedbacks:
        await callback.message.edit_text("✅ Нет неотвеченных отзывов!")
        return
    
    user_feedbacks[callback.from_user.id] = feedbacks

    await callback.message.edit_text(f" 📊 Найдено отзывов: {len(feedbacks)}. Выберите режим ответов на отзывы:\n\n РУЧНОЙ РЕЖИМ: отвечать на отзывы по одному, ИИ сгенерирует ответы.\n ОТВЕТИТЬ НА ВСЕ: Полностью автоматизированный процесс, действия от вас не нужны", reply_markup=answermod_keyboard())


@dp.callback_query(F.data == "reply_manual")
async def reply_manual(callback: types.CallbackQuery):
    await callback.message.edit_text("⌛ Отвечаем на отзывы в ручном режиме...")
    feedbacks = user_feedbacks.get(callback.from_user.id)
    if feedbacks is None:
        await callback.message.edit_text("❌ Ошибка в обработке отзывов, попробуйте снова", reply_markup=default_keyboard())
        return
    user_review_index[callback.from_user.id] = 0
    await show_next_review(callback.message.chat.id, callback.from_user.id)
    await callback.message.delete()

@dp.callback_query(F.data == "cancel_from_edit")
async def cancel_from_edit(callback: types.CallbackQuery):
    fb = user_feedbacks[callback.from_user.id][user_review_index[callback.from_user.id]]
    answer = pending_reviews[fb['id']]['answer']
    if fb.get('orderStatus') == "buyout":
        orderstatus = "выкуплен"
    if fb.get('orderStatus') == "rejected":
        orderstatus = "отказались"
    if fb.get('orderStatus') == "returned":
        orderstatus = "возврат"
    if fb.get('orderStatus') == "notSpecified":
        orderstatus = "статус не присвоен"
    review_text = f"Текст отзыва: {fb.get('text')}\nПлюсы: {fb.get('pros')} \nМинусы: {fb.get('cons')}\nСтатус заказа: {orderstatus}"

    start = "⭐" * fb["productValuation"]

    product = fb["productDetails"]["productName"]
    text = (
        f"👤 {fb['userName']} | {start}  Отзыв: {user_review_index[callback.from_user.id] + 1}/{len(user_feedbacks[callback.from_user.id])}\n"
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
        ),
        types.InlineKeyboardButton(
            text="Редактировать",
            callback_data=f"edit_{fb['id']}"
        ),
        types.InlineKeyboardButton(
            text="❌ Отменить",
            callback_data=f"cancel_review"
        )
    )
    builder.adjust(3, 1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


async def show_next_review(chat_id, user_id):
    if user_review_index[user_id] >= len(user_feedbacks[user_id]):
        await bot.send_message(chat_id, "✅ Обработка отзывов завершена!\n Продолжим работу? Проверте наличие отзывов!", reply_markup=default_keyboard())
        user_feedbacks.pop(user_id, None)
        user_review_index.pop(user_id, None)
        return

    fb = user_feedbacks[user_id][user_review_index[user_id]]
    answer = generate_answer(fb)

    if answer is None:
        user_review_index[user_id] += 1
        await show_next_review(chat_id, user_id)
        return
    
    #Сохраняем для кнопок
    pending_reviews[fb["id"]] = {
        "answer": answer,
        "feedback_id": fb["id"]
    }
    if fb.get('orderStatus') == "buyout":
        orderstatus = "выкуплен"
    if fb.get('orderStatus') == "rejected":
        orderstatus = "отказались"
    if fb.get('orderStatus') == "returned":
        orderstatus = "возврат"
    if fb.get('orderStatus') == "notSpecified":
        orderstatus = "статус не присвоен"
    review_text = f"Текст отзыва: {fb.get('text')}\nПлюсы: {fb.get('pros')} \nМинусы: {fb.get('cons')}\nСтатус заказа: {orderstatus}"

    start = "⭐" * fb["productValuation"]

    product = fb["productDetails"]["productName"]
    text = (
        f"👤 {fb['userName']} | {start}  Отзыв: {user_review_index[user_id] + 1}/{len(user_feedbacks[user_id])}\n"
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
        ),
        types.InlineKeyboardButton(
            text="Редактировать",
            callback_data=f"edit_{fb['id']}"
        ),
        types.InlineKeyboardButton(
            text="❌ Отменить",
            callback_data=f"cancel_review"
        )
    )
    builder.adjust(3, 1)
    await bot.send_message(chat_id, text, reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("send_"))
async def on_send(callback: types.CallbackQuery):
    feedback_id = callback.data.replace("send_", "")
    review = pending_reviews.get(feedback_id)

    if not review:
        await callback.answer("❌ Отзыв не найден")
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
        user_review_index[callback.from_user.id] += 1
        #await asyncio.sleep(0.5)
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ ОТПРАВЛЕНО"
        )
        await show_next_review(callback.message.chat.id, callback.from_user.id)
        del pending_reviews[feedback_id]
    else:
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(
            text="🔄 Попробовать снова",
            callback_data=f"send_{feedback_id}"
            ),
            types.InlineKeyboardButton(
            text="⏭️ Пропустить",
            callback_data=f"skip_{feedback_id}"
            )
        )
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ ОШИБКА ОТПРАВКИ",
            reply_markup=builder.as_markup()
        )
    await callback.answer()

@dp.callback_query(F.data.startswith("skip_"))
async def on_skip(callback: types.CallbackQuery):
    feedback_id = callback.data.replace("skip_", "")
    pending_reviews.pop(feedback_id, None)

    await callback.message.edit_text(
        callback.message.text + "\n\n⏭️ ПРОПУЩЕНО"
    )
    user_review_index[callback.from_user.id] += 1
    await show_next_review(callback.message.chat.id, callback.from_user.id)
    await callback.answer()

class EditState(StatesGroup):
    editing = State()
    
@dp.message(EditState.editing)
async def edit_review(message: Message, state: FSMContext):
    data = await state.get_data()
    feedback_id = data["feedback_id"]
    await state.clear()
    pending_reviews[feedback_id]["answer"] = message.text
    answer = pending_reviews[feedback_id]["answer"]
    fb = user_feedbacks[message.from_user.id][user_review_index[message.from_user.id]]
    pending_reviews[fb["id"]] = {
        "answer": answer,
        "feedback_id": fb["id"]
    }
    if fb.get('orderStatus') == "buyout":
        orderstatus = "выкуплен"
    if fb.get('orderStatus') == "rejected":
        orderstatus = "отказались"
    if fb.get('orderStatus') == "returned":
        orderstatus = "возврат"
    if fb.get('orderStatus') == "notSpecified":
        orderstatus = "статус не присвоен"
    review_text = f"Текст отзыва: {fb.get('text')}\nПлюсы: {fb.get('pros')} \nМинусы: {fb.get('cons')}\nСтатус заказа: {orderstatus}"

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
        ),
        types.InlineKeyboardButton(
            text="Редактировать",
            callback_data=f"edit_{fb['id']}"
        ),
        types.InlineKeyboardButton(
            text="❌ Отменить",
            callback_data=f"cancel_review"
        )
    )
    builder.adjust(3, 1)
    await message.answer(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("edit_"))
async def on_edit(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(
    types.InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="cancel_from_edit"
        )
    )
    feedback_id = callback.data.replace("edit_", "")
    review = pending_reviews.get(feedback_id)
    await state.update_data(feedback_id=feedback_id)
    if not review:
        await callback.answer("❌ Отзыв не найден")
        return
    
    await callback.message.edit_text(callback.message.text + "\n\n✍️ Введите новый ответ:", reply_markup=builder.as_markup())
    await state.set_state(EditState.editing)
    await callback.answer()


@dp.callback_query(F.data == "cancel_review")
async def on_cancel(callback: types.CallbackQuery):
    user_feedbacks.pop(callback.from_user.id, None)
    user_review_index.pop(callback.from_user.id, None)
    await callback.message.edit_text(callback.message.text +"\n\n   ❌ ОТМЕНЕНО",)
    await callback.message.answer(text="   🔧 Продолжим работу?", reply_markup=default_keyboard())
    await callback.answer()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())