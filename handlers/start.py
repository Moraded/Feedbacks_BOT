import aiohttp
import keyboards
from aiogram.filters import Command
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
from db import DatabaseBot
from wb_api import get_seller_info
from handlers.cabinets import callback_select_cabinet

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def command_start(message: types.Message, session: aiohttp.ClientSession, db: DatabaseBot):
    logger.info(f"Пользователь {message.from_user.id} начал работу с ботом")
    await db.register_user(message.from_user.id)
    token = await db.get_active_token(message.from_user.id)
    cabinets_status = await db.get_user_cabinets(message.from_user.id)
    if cabinets_status is None:
        await message.answer("❌ Ошибка при загрузки кабинетов, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
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
        try:
            seller_info = await get_seller_info(token, session)
            if seller_info is None:
                await message.answer("❌ Не удалось получить данные кабинета", reply_markup=keyboards.back_to_start_keyboard())
                return
            seller_name = seller_info.get("name")
            seller_id = seller_info.get("sid")
            seller_brand = seller_info.get("tradeMark")
        except aiohttp.ClientError as e:
            await message.answer("❌ Непредвиденная ошибка, попробуйте еще раз")
            return
        await message.answer(
            "* Готовы продолжить работу?\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Статус токена: ✅ Подключен\n\n"
            f"* Кабинет ВБ: {seller_name}"
            f" Бренд: {seller_brand}\n\n"
            "✉️ По всем вопросам писать @moraded451",
            reply_markup=keyboards.default_keyboard()
            )
        return
    else:
        list_user_cabinets = await db.get_user_cabinets(message.from_user.id)
        if not list_user_cabinets:
            await message.answer("❌ У вас нет сохраненных кабинетов, добавьте кабинет", reply_markup=keyboards.back_to_start_keyboard())
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
    

@router.callback_query(F.data == "callback_start")
async def callback_start(callback: types.CallbackQuery, session: aiohttp.ClientSession, db: DatabaseBot):
    await db.register_user(callback.from_user.id)
    token = await db.get_active_token(callback.from_user.id)
    cabinets_status = await db.get_user_cabinets(callback.from_user.id)
    if cabinets_status is None:
        await callback.message.edit_text("❌ Ошибка при загрузки кабинетов, попробуйте снова", reply_markup=keyboards.back_to_start_keyboard())
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
        try:
            seller_info = await get_seller_info(token, session)
            seller_name = seller_info.get("name")
            seller_id = seller_info.get("sid")
            seller_brand = seller_info.get("tradeMark")
        except:
            await callback.answer("❌ Непредвиденная ошибка, попробуйте еще раз")
            return
        if seller_info is None:
            await callback.message.edit_text("❌ Не удалось получить данные кабинета", reply_markup=keyboards.back_to_start_keyboard())
            await callback.answer()
            return
        await callback.message.edit_text(
            "* Готовы продолжить работу?\n\n"
            "* Маяк Селлеров - бот поможет вам автоматизировать процесс ответов на отзывы.\n\n"
            "* Статус токена: ✅ Подключен\n\n"
            f"* Кабинет ВБ: {seller_name}"
            f" Бренд: {seller_brand}\n\n"
            "✉️ По всем вопросам писать @moraded451",
            reply_markup=keyboards.default_keyboard()
            )
        await callback.answer()
        return
    else:
        await callback_select_cabinet(callback, db)
        await callback.answer()
        return