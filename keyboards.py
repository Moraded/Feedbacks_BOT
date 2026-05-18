from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def return_keyboard(buttons):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def review_action_keyboard(feedback_id: str):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="✅ Отправить",   callback_data=f"send_{feedback_id}"),
        types.InlineKeyboardButton(text="⏭️ Пропустить",  callback_data=f"skip_{feedback_id}"),
        types.InlineKeyboardButton(text="Редактировать",  callback_data=f"edit_{feedback_id}"),
        types.InlineKeyboardButton(text="❌ Отменить",    callback_data="cancel_review")
    )
    builder.adjust(3, 1)
    return builder.as_markup()

#кнопка "Настройки кабинета"
def cabinets_opt_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="▶️ Выбрать кабинет", callback_data="select_cabinet")],
        [types.InlineKeyboardButton(text="🔑 Добавить кабинет", callback_data="add_cabinet")],
        [types.InlineKeyboardButton(text="🔄 Сбросить токен текущего кабинета", callback_data="token_reset")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)

#кнопка "Назад" вызывает стартовое меню
def back_to_start_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)

#кнопки выбора режима ответов на отзывы, вызывают соответствующие функции
def answermod_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="✍️ Ручной режим", callback_data="reply_manual")],
        [types.InlineKeyboardButton(text="🤖 Ответить на все", callback_data="reply_auto")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)

#стартовое меню, после регистрации хотя бы одного кабинета ВБ
def default_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="📝 Ответить на отзывы", callback_data="reviews")],
        [types.InlineKeyboardButton(text="🔎 Проверить наличие отзывов", callback_data="check_update")],
        [types.InlineKeyboardButton(text="👤 Настройки кабинета",
        callback_data="cabinets_opt")]
    ]
    return return_keyboard(buttons)

#кнопки подключения токена
def connect_token_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
            [types.InlineKeyboardButton(text="➡️🔑 Подключить токен", callback_data="token_connect")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)