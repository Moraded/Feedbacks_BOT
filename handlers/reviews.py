import aiohttp
import keyboards
from aiogram.types import Message
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from db import DatabaseBot
from ai import generate_answer
import asyncio
from wb_api import check_token, send_answer_to_wb, get_wb_feedbacks
from storage import pending_reviews, user_feedbacks, user_review_index, flag_stop_reply_auto


router = Router()

@router.callback_query(F.data == "reviews")
async def callback_reviews(callback: types.CallbackQuery, session: aiohttp.ClientSession, db: DatabaseBot):
    await callback.message.edit_text("⌛ Загружаю отзывы с WB...")
    token = await db.get_active_token(callback.from_user.id)
    if not token:
        await callback.message.edit_text("❌ Токен отсутствует!", reply_markup=keyboards.connect_token_keyboard())
        return
    feedbacks = await get_wb_feedbacks(token, session)
    #Проверка на ошибки загрузки
    if feedbacks is None:
        await callback.message.edit_text(f"❌ Ошибка загрузки ответов с WB", reply_markup=keyboards.back_to_start_keyboard())
        return
    if not feedbacks:
        await callback.message.edit_text("✅ Нет неотвеченных отзывов!", reply_markup=keyboards.back_to_start_keyboard())
        return
    
    user_feedbacks[callback.from_user.id] = feedbacks

    await callback.message.edit_text(f" 📊 Найдено отзывов: {len(feedbacks)}. Выберите режим ответов на отзывы:\n\n ✍️ РУЧНОЙ РЕЖИМ: отвечать на отзывы по одному, ИИ сгенерирует ответы.\n⚙️ ОТВЕТИТЬ НА ВСЕ: Полностью автоматизированный процесс, действия от вас не нужны", reply_markup=keyboards.answermod_keyboard())
    

@router.callback_query(F.data == "check_update")
async def callback_check_update(callback: types.CallbackQuery, session: aiohttp.ClientSession, db: DatabaseBot):
    await callback.message.edit_text("⌛ Сканирую отзывы с WB...")
    token = await db.get_active_token(callback.from_user.id)
    seller_name = await db.get_user_seller_name(token)
    if not token:
        await callback.message.edit_text("Токен отсутствует, попробуйте сначала ввести токен", reply_markup=keyboards.connect_token_keyboard())
        return
    feedbacks = await get_wb_feedbacks(token, session)
    if feedbacks is None:
        await callback.message.edit_text(f"❌ Ошибка загрузки ответов с WB", reply_markup=keyboards.default_keyboard())
        return
    if not feedbacks:
        await callback.message.edit_text("✅ Нет неотвеченных отзывов!", reply_markup=keyboards.back_to_start_keyboard())
        return
    
    user_feedbacks[callback.from_user.id] = feedbacks

    await callback.message.edit_text(f"У вас есть новые отзывы! 📊 Найдено отзывов: {len(feedbacks)}\n\n👤 Активный кабинет: {seller_name}", reply_markup=keyboards.default_keyboard())


async def show_next_review(chat_id, user_id, bot):
    if user_review_index[user_id] >= len(user_feedbacks[user_id]):
        await bot.send_message(chat_id, "✅ Обработка отзывов завершена!\n Продолжим работу? Проверьте наличие отзывов!", reply_markup=keyboards.default_keyboard())
        user_feedbacks.pop(user_id, None)
        user_review_index.pop(user_id, None)
        return
    review_number = user_review_index[user_id] + 1
    fb = user_feedbacks[user_id][user_review_index[user_id]]
    answer = await generate_answer(fb, review_number)

    if answer is None:
        user_review_index[user_id] += 1
        await show_next_review(chat_id, user_id, bot)
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


@router.callback_query(F.data == "reply_manual")
async def reply_manual(callback: types.CallbackQuery):
    await callback.message.edit_text("⌛ Отвечаем на отзывы в ручном режиме...")
    feedbacks = user_feedbacks.get(callback.from_user.id)
    if feedbacks is None:
        await callback.message.edit_text("❌ Ошибка в обработке отзывов, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    user_review_index[callback.from_user.id] = 0
    await show_next_review(callback.message.chat.id, callback.from_user.id, callback.bot)
    await callback.message.delete()
    

@router.callback_query(F.data == "reply_auto")
async def reply_auto(callback: types.CallbackQuery, session: aiohttp.ClientSession, db: DatabaseBot, ai_semaphore: asyncio.Semaphore):
    await callback.answer()
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
        await callback.message.edit_text("❌ Ошибка в обработке отзывов, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    token = await db.get_active_token(callback.from_user.id)
    if token is None:
        await callback.message.edit_text("❌ Ошибка чтения токена", reply_markup=keyboards.back_to_start_keyboard())
        return
    token_status = await check_token(token, session)
    if not token_status:
        await callback.message.edit_text("❌ Непредвиденная ошибка при проверке токена, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    if token_status != 200:
        await callback.message.edit_text("❌ Ошибка токена, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    counter = 0
    error_counter = 0
    await callback.message.edit_text(f"⌛ Обработка отзывов в процессе, пожалуйста, подождите...\n\n")
    flag_stop_reply_auto[callback.from_user.id] = False
    for fb in feedbacks:
        flag = flag_stop_reply_auto.get(callback.from_user.id)
        if flag == True:
            await callback.message.edit_text("❌ Обработка отзывов остановлена.", reply_markup=keyboards.back_to_start_keyboard())
            flag_stop_reply_auto[callback.from_user.id] = False
            user_feedbacks.pop(callback.from_user.id, None)
            user_review_index.pop(callback.from_user.id, None)
            return
        counter += 1
        await callback.message.edit_text(f"⌛ Отвечаем на отзыв {counter} из {len(feedbacks)}...", reply_markup=builder.as_markup())

        async with ai_semaphore:
            answer = await generate_answer(fb, counter)

        if answer is None:
            error_counter += 1
            await callback.message.edit_text(f"❌ Ошибка генерации ответа на отзыв {counter} из {len(feedbacks)}")
            if error_counter > 5:
                await callback.message.edit_text(f"❌ Произошла критическа ошибка, попробуйте снова позже", reply_markup=keyboards.back_to_start_keyboard())
                return
            continue
        succes = await send_answer_to_wb (fb["id"], answer, token, session)
        if succes is None:
            error_counter += 1
            await callback.message.edit_text("❌ Ошибка в отправке ответа на WB")
            if error_counter > 5:
                await callback.message.edit_text(f"❌ Произошла критическа ошибка, попробуйте снова позже", reply_markup=keyboards.back_to_start_keyboard())
                return
            continue
        if error_counter >= 1:
            error_counter -=1
    await callback.message.edit_text(f"✅ Обработка отзывов завершена!\n\n Продолжим работу? Проверьте наличие отзывов!", reply_markup=keyboards.default_keyboard())

    user_feedbacks.pop(callback.from_user.id, None)
    user_review_index.pop(callback.from_user.id, None)
    
	
@router.callback_query(F.data == "callback_stop_reply_auto")
async def stop_reply_auto(callback: types.CallbackQuery):
    flag_stop_reply_auto[callback.from_user.id] = True

@router.callback_query(F.data == "cancel_from_edit")
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
    

@router.callback_query(F.data.startswith("send_"))
async def on_send(callback: types.CallbackQuery, session: aiohttp.ClientSession, db: DatabaseBot):
    feedback_id = callback.data.replace("send_", "")
    review = pending_reviews.get(feedback_id)

    if not review:
        await callback.answer("❌ Отзыв не найден")
        return
    try:
        token = await db.get_active_token(callback.from_user.id)
        success = await send_answer_to_wb(feedback_id, review["answer"], token, session)
    except (aiohttp.ClientError, KeyError, ValueError):
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ ОШИБКА API", reply_markup=keyboards.back_to_start_keyboard()
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
        await show_next_review(callback.message.chat.id, callback.from_user.id, callback.bot)
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

@router.callback_query(F.data.startswith("skip_"))
async def on_skip(callback: types.CallbackQuery):
    feedback_id = callback.data.replace("skip_", "")
    pending_reviews.pop(feedback_id, None)

    await callback.message.edit_text(
        callback.message.text + "\n\n⏭️ ПРОПУЩЕНО"
    )
    user_review_index[callback.from_user.id] += 1
    await show_next_review(callback.message.chat.id, callback.from_user.id, callback.bot)
    await callback.answer()

class EditState(StatesGroup):
    editing = State()
    
@router.message(EditState.editing)
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
    elif fb.get('orderStatus') == "rejected":
        orderstatus = "отказались"
    elif fb.get('orderStatus') == "returned":
        orderstatus = "возврат"
    elif fb.get('orderStatus') == "notSpecified":
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


@router.callback_query(F.data.startswith("edit_"))
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


@router.callback_query(F.data == "cancel_review")
async def on_cancel(callback: types.CallbackQuery):
    user_feedbacks.pop(callback.from_user.id, None)
    user_review_index.pop(callback.from_user.id, None)
    await callback.message.edit_text(callback.message.text +"\n\n   ❌ ОТМЕНЕНО", reply_markup=keyboards.back_to_start_keyboard())
    await callback.answer()