from aiogram import types



def return_keyboadr(buttons: list[list[types.InlineKeyboardButton]]) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#кнопка "Настройки кабинета"
def cabinets_opt_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="▶️ Выбрать кабинет", callback_data="select_cabinet")],
        [types.InlineKeyboardButton(text="🔑 Добавить кабинет", callback_data="add_cabinet")],
        [types.InlineKeyboardButton(text="🔄 Сбросить токен текущего кабинета", callback_data="token_reset")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboadr(buttons)

#кнопка "Назад" вызывает стартовое меню
def back_to_start_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboadr(buttons)

#кнопки выбора режима ответов на отзывы, вызывают соответствующие функции
def answermod_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="✍️ Ручной режим", callback_data="reply_manual")],
        [types.InlineKeyboardButton(text="🤖 Ответить на все", callback_data="reply_auto")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboadr(buttons)

#стартовое меню, после регистрации хотя бы одного кабинета ВБ
def default_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="📝 Ответить на отзывы", callback_data="reviews")],
        [types.InlineKeyboardButton(text="🔎 Проверить наличие отзывов", callback_data="check_update")],
        [types.InlineKeyboardButton(text="👤 Настройки кабинета",
        callback_data="cabinets_opt")]
    ]
    return return_keyboadr(buttons)

#кнопки подключения токена
def connect_token_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
            [types.InlineKeyboardButton(text="➡️🔑 Подключить токен", callback_data="token_connect")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboadr(buttons)