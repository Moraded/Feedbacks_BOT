from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from db import DatabaseBot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
import aiohttp
import keyboards
from wb_api import check_token, get_seller_info


router = Router()


class WaitToken(StatesGroup):
    wait_token = State()
    

@router.callback_query(F.data == "select_cabinet")
async def callback_select_cabinet(callback: types.CallbackQuery, db: DatabaseBot):
    list_user_cabinets = await db.get_user_cabinets(callback.from_user.id)
    if not list_user_cabinets:
        await callback.message.edit_text("❌ У вас нет сохраненных кабинетов, добавьте кабинет", reply_markup=keyboards.back_to_start_keyboard())
        return
    builder = InlineKeyboardBuilder()
    for cabinet in list_user_cabinets:
        button_text = f"{cabinet['seller_name']} | {cabinet['brand_name']}"
        if cabinet["is_active"]:
            button_text += " ✅"
        builder.add(
            types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"switch_{cabinet['id']}"
            )
        )
    builder.add(
        types.InlineKeyboardButton(
            text="◀️ Назад", callback_data="callback_start"
        )
    )
    builder.adjust(1)
    await callback.message.edit_text("📂 Выберите кабинет для работы:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("switch_"))
async def callback_switch_cabinet(callback: types.CallbackQuery, db: DatabaseBot):
    cabinet_id = callback.data.replace("switch_", "")
    if not await db.switch_cabinet(callback.from_user.id, cabinet_id):
        await callback.message.edit_text("❌ Ошибка при переключении кабинета, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    await callback_select_cabinet(callback, db)
    

@router.callback_query(F.data == "add_cabinet")
async def callback_add_cabinet(callback: types.CallbackQuery, state: FSMContext):
    msg = await callback.message.edit_text("🔑 Введите токен для нового кабинета:")
    await state.update_data(message_id=msg.message_id)
    await state.set_state(WaitToken.wait_token)
    await callback.answer()
    

@router.callback_query(F.data == "token_reset")
async def callback_token_reset(callback: types.CallbackQuery, db: DatabaseBot):
    token = await db.get_active_token(callback.from_user.id)
    if not await db.reset_token(callback.from_user.id, token):
        await callback.message.edit_text("❌ Ошибка сброса токена, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    await callback.message.edit_text("✅ Токен сброшен!", reply_markup=keyboards.back_to_start_keyboard())
    await callback.answer()
    

@router.callback_query(F.data == "cabinets_opt")
async def callback_cabinets_opt(callback: types.CallbackQuery, db: DatabaseBot):
    token = await db.get_active_token(callback.from_user.id)
    seller_name = await db.get_user_seller_name(token)
    await callback.message.edit_text(f"✅ Активный кабинет: {seller_name}\n\n👤 Настройки кабинета:", reply_markup=keyboards.cabinets_opt_keyboard())
    

@router.callback_query(F.data == "token_connect")
async def start_token_connect(callback: types.CallbackQuery, state: FSMContext):
    msg = await callback.message.edit_text("🔑 Введите токен:")
    await state.update_data(message_id=msg.message_id)
    await state.set_state(WaitToken.wait_token)
    await callback.answer()
    

@router.callback_query(F.data == "token_replace")
async def start_token_replace(callback: types.CallbackQuery, state: FSMContext):
    msg = await callback.message.edit_text("🔑 Введите новый токен:")
    await state.update_data(message_id=msg.message_id)
    await state.set_state(WaitToken.wait_token)
    await callback.answer()
    

@router.message(WaitToken.wait_token)
async def insert_token(message: Message, state: FSMContext, session: aiohttp.ClientSession, db: DatabaseBot):
    data = await state.get_data()
    status_msg = await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=data.get("message_id"),
        text="⌛ Проверяю токен..."
    )
    token = message.text.strip()
    await message.delete()
    await state.clear()
    token_status = await check_token(token, session)
    if token_status is None:
        await status_msg.edit_text("❌ Непредвиденная ошибка при проверке токена, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    if token_status == 200:
        seller_info = await get_seller_info(token, session)
        if seller_info is not None:
            seller_name = seller_info.get("name")
            brand_name = seller_info.get("tradeMark")
            if not seller_name or not brand_name:
                await status_msg.edit_text("❌ Не удалось обработать имя продавца попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
                return
            add_cabinet_status = await db.add_cabinet(message.from_user.id, token, seller_name, brand_name)
            if add_cabinet_status == "duplicate":
                await status_msg.edit_text("❌ Скорее всего такой токен уже существует, проверьте в списке подключенных кабинетов", reply_markup=keyboards.back_to_start_keyboard())
                return
            if not add_cabinet_status:
                await status_msg.edit_text("❌ Непредвиденная ошибка, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
                return
            await status_msg.edit_text("✅🔑 Токен успешно подтвержден!", reply_markup=keyboards.back_to_start_keyboard())
            return
        return
    elif token_status == 401:
        await status_msg.edit_text("❌🔑 Неверный токен или не авторизован!", reply_markup=keyboards.back_to_start_keyboard())
        return
    elif token_status == 429:
        await status_msg.edit_text("❌ 🕒 Слишком много запросов!", reply_markup=keyboards.back_to_start_keyboard())
        return
    else:
        await status_msg.edit_text("❌ Другая ошибка токена!", reply_markup=keyboards.back_to_start_keyboard())
        return
    

@router.message(Command("reset"))
async def cmd_reset(message: types.Message, db: DatabaseBot):
    token = await db.get_active_token(message.from_user.id)
    if not await db.reset_token(message.from_user.id, token):
        await message.answer("❌ Ошибка сброса токена, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    await message.answer("✅ Токен сброшен!", reply_markup=keyboards.back_to_start_keyboard())


@router.message(StateFilter(None), Command("token"))
async def cmd_token(message: Message, state: FSMContext):
    await message.answer(
        text="🔑 Введите токен:",
    )
    await state.set_state(WaitToken.wait_token)

@router.message(WaitToken.wait_token)
async def insert_token(message: Message, state: FSMContext, session: aiohttp.ClientSession, db: DatabaseBot):
    data = await state.get_data()
    status_msg = await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=data.get("message_id"),
        text="⌛ Проверяю токен..."
    )
    token = message.text.strip()
    await message.delete()
    await state.clear()
    token_status = await check_token(token, session)
    if token_status is None:
        await status_msg.edit_text("❌ Непредвиденная ошибка при проверке токена, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
        return
    if token_status == 200:
        seller_info = await get_seller_info(token, session)
        if seller_info is not None:
            seller_name = seller_info.get("name")
            brand_name = seller_info.get("tradeMark")
            if not seller_name or not brand_name:
                await status_msg.edit_text("❌ Не удалось обработать имя продавца попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
                return
            add_cabinet_status = await db.add_cabinet(message.from_user.id, token, seller_name, brand_name)
            if add_cabinet_status == "duplicate":
                await status_msg.edit_text("❌ Скорее всего такой токен уже существует, проверьте в списке подключенных кабинетов", reply_markup=keyboards.back_to_start_keyboard())
                return
            if not add_cabinet_status:
                await status_msg.edit_text("❌ Непредвиденная ошибка, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
                return
            await status_msg.edit_text("✅🔑 Токен успешно подтвержден!", reply_markup=keyboards.back_to_start_keyboard())
            return
        return
    elif token_status == 401:
        await status_msg.edit_text("❌🔑 Неверный токен или не авторизован!", reply_markup=keyboards.back_to_start_keyboard())
        return
    elif token_status == 429:
        await status_msg.edit_text("❌ 🕒 Слишком много запросов!", reply_markup=keyboards.back_to_start_keyboard())
        return
    else:
        await status_msg.edit_text("❌ Другая ошибка токена!", reply_markup=keyboards.back_to_start_keyboard())
        return
    return