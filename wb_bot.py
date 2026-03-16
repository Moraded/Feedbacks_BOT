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
from db import register_user, get_active_token, init_db, add_cabinet,reset_token, get_user_cabinets, switch_cabinet, get_user_seller_name
from wb_api import get_wb_feedbacks, send_answer_to_wb, check_token, get_seller_info
from ai import generate_answer


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


#Хранилище отзывов для кнопок
pending_reviews = {}
#Хранилище отзывов для режима ответов
user_feedbacks = {}
#Индекс для отслеживания текущего отзыва в ручном режиме
user_review_index = {}
#ID активного кабинета
active_cabinet_id = {}
#Флаг для остановки ответов в автоматизированом режиме
flag_stop_reply_auto = {}



class WaitToken(StatesGroup):
    wait_token = State()

#Клавиатуры
def cabinets_opt_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="▶️ Выбрать кабинет", callback_data="select_cabinet")],
        [types.InlineKeyboardButton(text="🔑 Добавить кабинет", callback_data="add_cabinet")],
        [types.InlineKeyboardButton(text="🔄 Сбросить токен текущего кабинета", callback_data="token_reset")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard



@dp.callback_query(F.data == "select_cabinet")
async def callback_select_cabinet(callback: types.CallbackQuery):
    list_user_cabinets = get_user_cabinets(callback.from_user.id)
    if not list_user_cabinets:
        await callback.message.edit_text("❌ У вас нет сохраненных кабинетов, добавьте кабинет", reply_markup=back_to_start_keyboard())
        return
    builder = InlineKeyboardBuilder()
    for cabinet in list_user_cabinets:
        cabinet_id = cabinet[0]
        seller_name = cabinet[1]
        brand_name = cabinet[2]
        is_active = cabinet[3]
        button_text = f"{seller_name} | {brand_name}"
        if is_active:
            button_text += " ✅"
        builder.add(
            types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"switch_{cabinet_id}"
            )
        )
    builder.add(
        types.InlineKeyboardButton(
            text="◀️ Назад", callback_data="callback_start"
        )
    )
    builder.adjust(1)
    await callback.message.edit_text("📂 Выберите кабинет для работы:", reply_markup=builder.as_markup())



@dp.callback_query(F.data.startswith("switch_"))
async def callback_switch_cabinet(callback: types.CallbackQuery):
    cabinet_id = callback.data.replace("switch_", "")
    if not switch_cabinet(callback.from_user.id, cabinet_id):
        await callback.message.edit_text("❌ Ошибка при переключении кабинета, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    await callback_select_cabinet(callback)



@dp.callback_query(F.data == "add_cabinet")
async def callback_add_cabinet(callback: types.CallbackQuery, state: FSMContext):
    msg = await callback.message.edit_text("🔑 Введите токен для нового кабинета:")
    await state.update_data(message_id=msg.message_id)
    await state.set_state(WaitToken.wait_token)
    await callback.answer()



def back_to_start_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard



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
        [types.InlineKeyboardButton(text="📝 Ответить на отзывы", callback_data="reviews")],
        [types.InlineKeyboardButton(text="🔎 Проверить наличие отзывов", callback_data="check_update")],
        [types.InlineKeyboardButton(text="👤 Настройки кабинета",
        callback_data="cabinets_opt")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

@dp.callback_query(F.data == "cabinets_opt")
async def callback_cabinets_opt(callback: types.CallbackQuery):
    token = get_active_token(callback.from_user.id)
    seller_name = get_user_seller_name(token)
    await callback.message.edit_text(f"✅ Активный кабинет: {seller_name}\n\n👤 Настройки кабинета:", reply_markup=cabinets_opt_keyboard())



def connect_token_keyboard():
    buttons = [
            [types.InlineKeyboardButton(text="➡️🔑 Подключить токен", callback_data="token_connect")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard



@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    token = get_active_token(message.from_user.id)
    if not reset_token(message.from_user.id, token):
        await message.answer("❌ Ошибка сброса токена, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    await message.answer("✅ Токен сброшен!", reply_markup=back_to_start_keyboard())



@dp.callback_query(F.data == "token_reset")
async def callback_token_reset(callback: types.CallbackQuery):
    token = get_active_token(callback.from_user.id)
    if not reset_token(callback.from_user.id, token):
        await callback.message.edit_text("❌ Ошибка сброса токена, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    await callback.message.edit_text("✅ Токен сброшен!", reply_markup=back_to_start_keyboard())
    await callback.answer()



@dp.callback_query(F.data == "callback_start")
async def callback_start(callback: types.CallbackQuery):
    register_user(callback.from_user.id)
    token = get_active_token(callback.from_user.id)
    cabinets_status = get_user_cabinets(callback.from_user.id)
    if cabinets_status is None:
        await callback.message.edit_text("❌ Ошибка при загрузки кабинетов, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    if not cabinets_status:
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(text="➡️🔑 Подключить токен", callback_data="token_connect")
        )
        await callback.message.edit_text(
            "* Для того, чтобы использовать бота, необходимо подключить API токен кабинета. Достаточно создать новый токен в кабинете WB с доступом к категории 'вопросы и отзывы (чтение и запись)'\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Бот через API токен кабинета получает данные о отзывах, обрабатывает и генерирует ответы.\n\n"
            "* Статус токена: ❌ Не подключен", reply_markup=builder.as_markup()
            )
        await callback.answer()
        return
    elif token:
        seller_info = get_seller_info(token)
        seller_name = seller_info.get("name")
        seller_id = seller_info.get("sid")
        seller_brand = seller_info.get("tradeMark")
        if seller_info is None:
            await callback.message.edit_text("❌ Не удалось получить данные кабинета", reply_markup=back_to_start_keyboard())
            await callback.answer()
            return
        await callback.message.edit_text(
            "* Готовы продолжить работу?\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Статус токена: ✅ Подключен\n\n"
            f"* Кабинет ВБ: {seller_name}"
            f" Бренд: {seller_brand}\n\n"
            "✉️ По всем вопросам писать @moraded451",
            reply_markup=default_keyboard()
            )
        await callback.answer()
        return
    else:
        await callback_select_cabinet(callback)
        await callback.answer()
        return



@dp.message(Command("start"))
async def command_start(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} начал работу с ботом")
    register_user(message.from_user.id)
    token = get_active_token(message.from_user.id)
    cabinets_status = get_user_cabinets(message.from_user.id)
    if cabinets_status is None:
        await message.answer("❌ Ошибка при загрузки кабинетов, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    if not cabinets_status:
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(text="➡️🔑 Подключить токен", callback_data="token_connect")
        )
        await message.answer(
            "* Для того, чтобы использовать бота, необходимо подключить API токен кабинета. Достаточно создать новый токен в кабинете WB с доступом к категории 'вопросы и отзывы (чтение и запись)'\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Бот через API токен кабинета получает данные о отзывах, обрабатывает и генерирует ответы.\n\n"
            "* Статус токена: ❌ Не подключен", reply_markup=builder.as_markup()
            )
        return
    elif token:
        seller_info = get_seller_info(token)
        seller_name = seller_info.get("name")
        seller_id = seller_info.get("sid")
        seller_brand = seller_info.get("tradeMark")
        if seller_info is None:
            await message.answer("❌ Не удалось получить данные кабинета", reply_markup=back_to_start_keyboard())
            return
        await message.answer(
            "* Готовы продолжить работу?\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Статус токена: ✅ Подключен\n\n"
            f"* Кабинет ВБ: {seller_name}"
            f" Бренд: {seller_brand}\n\n"
            "✉️ По всем вопросам писать @moraded451",
            reply_markup=default_keyboard()
            )
        return
    else:
        list_user_cabinets = get_user_cabinets(message.from_user.id)
        if not list_user_cabinets:
            await message.answer("❌ У вас нет сохраненных кабинетов, добавьте кабинет", reply_markup=back_to_start_keyboard())
            return
        builder = InlineKeyboardBuilder()
        for cabinet in list_user_cabinets:
            cabinet_id = cabinet[0]
            seller_name = cabinet[1]
            brand_name = cabinet[2]
            is_active = cabinet[3]
            button_text = f"{seller_name} | {brand_name}"
            if is_active:
                button_text += " ✅"
            builder.add(
                types.InlineKeyboardButton(
                text=button_text,
                    callback_data=f"switch_{cabinet_id}"
                )
            )
        builder.adjust(1)
        await message.answer("📂 Выберите кабинет для работы:", reply_markup=builder.as_markup())
        return



@dp.callback_query(F.data == "check_update")
async def callback_check_update(callback: types.CallbackQuery):
    await callback.message.edit_text("⌛ Сканирую отзывы с WB...")
    token = get_active_token(callback.from_user.id)
    seller_name = get_user_seller_name(token)
    if not token:
        await callback.message.edit_text("Токен отсутствует, попробуйте сначала ввести токен", reply_markup=connect_token_keyboard())
        return
    feedbacks = await asyncio.to_thread(get_wb_feedbacks, token)
    if feedbacks is None:
        await callback.message.edit_text(f"❌ Ошибка загрузки ответов с WB", reply_markup=default_keyboard())
        return
    if not feedbacks:
        await callback.message.edit_text("✅ Нет неотвеченных отзывов!", reply_markup=back_to_start_keyboard())
        return
    
    user_feedbacks[callback.from_user.id] = feedbacks

    await callback.message.edit_text(f"У вас есть новые отзывы! 📊 Найдено отзывов: {len(feedbacks)}\n\n👤 Активный кабинет: {seller_name}", reply_markup=default_keyboard())



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
    if token_status is None:
        await status_msg.edit_text("❌ Непредвиденная ошибка при проверке токена, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    if token_status == 200:
        seller_info = get_seller_info(token)
        if seller_info is not None:
            seller_name = seller_info.get("name")
            brand_name = seller_info.get("tradeMark")
            if not seller_name or not brand_name:
                await status_msg.edit_text("❌ Не удалось обработать имя продавца попробуйте снова", reply_markup=back_to_start_keyboard())
                return
            add_cabinet_status = add_cabinet(message.from_user.id, token, seller_name, brand_name)
            if add_cabinet_status == "duplicate":
                await status_msg.edit_text("❌ Скорее всего такой токен уже существует, проверьте в списке подключенных кабинетов", reply_markup=back_to_start_keyboard())
                return
            if not add_cabinet_status:
                await status_msg.edit_text("❌ Непредвиденная ошибка, попробуйте снова", reply_markup=back_to_start_keyboard())
                return
            await status_msg.edit_text("✅🔑 Токен успешно подтвержден!", reply_markup=back_to_start_keyboard())
            return
        return
    elif token_status == 401:
        await status_msg.edit_text("❌🔑 Неверный токен или не авторизован!", reply_markup=back_to_start_keyboard())
        return
    elif token_status == 429:
        await status_msg.edit_text("❌ 🕒 Слишком много запросов!", reply_markup=back_to_start_keyboard())
        return
    else:
        await status_msg.edit_text("❌ Другая ошибка токена!", reply_markup=back_to_start_keyboard())
        return
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
    token = get_active_token(callback.from_user.id)
    if not token:
        await callback.message.edit_text("❌ Токен отсутствует!", reply_markup=connect_token_keyboard())
        return
    feedbacks = await asyncio.to_thread(get_wb_feedbacks, token)
    #Проверка на ошибки загрузки
    if feedbacks is None:
        await callback.message.edit_text(f"❌ Ошибка загрузки ответов с WB", reply_markup=back_to_start_keyboard())
        return
    if not feedbacks:
        await callback.message.edit_text("✅ Нет неотвеченных отзывов!", reply_markup=back_to_start_keyboard())
        return
    
    user_feedbacks[callback.from_user.id] = feedbacks

    await callback.message.edit_text(f" 📊 Найдено отзывов: {len(feedbacks)}. Выберите режим ответов на отзывы:\n\n ✍️ РУЧНОЙ РЕЖИМ: отвечать на отзывы по одному, ИИ сгенерирует ответы.\n⚙️ ОТВЕТИТЬ НА ВСЕ: Полностью автоматизированный процесс, действия от вас не нужны", reply_markup=answermod_keyboard())



@dp.callback_query(F.data == "reply_manual")
async def reply_manual(callback: types.CallbackQuery):
    await callback.message.edit_text("⌛ Отвечаем на отзывы в ручном режиме...")
    feedbacks = user_feedbacks.get(callback.from_user.id)
    if feedbacks is None:
        await callback.message.edit_text("❌ Ошибка в обработке отзывов, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    user_review_index[callback.from_user.id] = 0
    await show_next_review(callback.message.chat.id, callback.from_user.id)
    await callback.message.delete()



@dp.callback_query(F.data == "reply_auto")
async def reply_auto(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text = "❌ Отмена",
            callback_data="callback_stop_reply_auto"
        )
    )
    await callback.message.edit_text("⌛ Отвечаем на отзывы в автоматическом режиме...")
    feedbacks = user_feedbacks.get(callback.from_user.id)
    if feedbacks is None:
        await callback.message.edit_text("❌ Ошибка в обработке отзывов, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    token = get_active_token(callback.from_user.id)
    if token is None:
        await callback.message.edit_text("❌ Ошибка чтения токена", reply_markup=back_to_start_keyboard())
        return
    token_status = check_token(token)
    if not token_status:
        await callback.message.edit_text("❌ Непредвиденная ошибка при проверке токена, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    if token_status != 200:
        await callback.message.edit_text("❌ Ошибка токена, попробуйте снова", reply_markup=back_to_start_keyboard())
        return
    counter = 0
    error_counter = 0
    await callback.message.edit_text(f"⌛ Обработка отзывов в процессе, пожалуйста, подождите...\n\n")
    flag_stop_reply_auto[callback.from_user.id] = False
    for fb in feedbacks:
        flag = flag_stop_reply_auto.get(callback.from_user.id)
        if flag == True:
            await callback.message.edit_text("❌ Обработка отзывов остановлена.", reply_markup=back_to_start_keyboard())
            flag_stop_reply_auto[callback.from_user.id] = False
            user_feedbacks.pop(callback.from_user.id, None)
            user_review_index.pop(callback.from_user.id, None)
            return
        counter += 1
        await asyncio.sleep(0.5)
        await callback.message.edit_text(f"⌛ Отвечаем на отзыв {counter} из {len(feedbacks)}...", reply_markup=builder.as_markup())
        answer = await asyncio.to_thread(generate_answer, fb, counter)
        if answer is None:
            error_counter += 1
            await callback.message.edit_text(f"❌ Ошибка генерации ответа на отзыв {counter} из {len(feedbacks)}")
            if error_counter > 5:
                await callback.message.edit_text(f"❌ Произошла критическа ошибка, попробуйте снова позже", reply_markup=back_to_start_keyboard())
                return
            continue
        succes = await asyncio.to_thread(send_answer_to_wb, fb["id"], answer, token)
        if succes is None:
            error_counter += 1
            await callback.message.edit_text("❌ Ошибка в отправке ответа на WB")
            continue
        if error_counter >= 1:
            error_counter -=1
    await callback.message.edit_text(f"✅ Обработка отзывов завершена!\n\n Продолжим работу? Проверьте наличие отзывов!", reply_markup=default_keyboard())

    user_feedbacks.pop(callback.from_user.id, None)
    user_review_index.pop(callback.from_user.id, None)
    await callback.answer()

@dp.callback_query(F.data == "callback_stop_reply_auto")
async def stop_reply_auto(callback: types.CallbackQuery):
    flag_stop_reply_auto[callback.from_user.id] = True

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
        await bot.send_message(chat_id, "✅ Обработка отзывов завершена!\n Продолжим работу? Проверьте наличие отзывов!", reply_markup=default_keyboard())
        user_feedbacks.pop(user_id, None)
        user_review_index.pop(user_id, None)
        return
    review_number = user_review_index[user_id] + 1
    fb = user_feedbacks[user_id][user_review_index[user_id]]
    answer = await asyncio.to_thread(generate_answer, fb, review_number)

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
        token = get_active_token(callback.from_user.id)
        success = await asyncio.to_thread(send_answer_to_wb, feedback_id, review["answer"], token)
    except requests.exceptions.RequestException:
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ ОШИБКА API", reply_markup=back_to_start_keyboard()
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
    await callback.message.edit_text(callback.message.text +"\n\n   ❌ ОТМЕНЕНО", reply_markup=back_to_start_keyboard())
    await callback.answer()



async def main():
    logger.info("Бот запущен")
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())