from aiogram import types



def return_keyboard(buttons):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def cabinets_opt_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="▶️ Выбрать кабинет", callback_data="select_cabinet")],
        [types.InlineKeyboardButton(text="🔑 Добавить кабинет", callback_data="add_cabinet")],
        [types.InlineKeyboardButton(text="🔄 Сбросить токен текущего кабинета", callback_data="token_reset")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)


def back_to_start_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)


def answermod_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="✍️ Ручной режим", callback_data="reply_manual")],
        [types.InlineKeyboardButton(text="🤖 Ответить на все", callback_data="reply_auto")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)


def default_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="📝 Ответить на отзывы", callback_data="reviews")],
        [types.InlineKeyboardButton(text="🔎 Проверить наличие отзывов", callback_data="check_update")],
        [types.InlineKeyboardButton(text="👤 Настройки кабинета",
        callback_data="cabinets_opt")]
    ]
    return return_keyboard(buttons)


def connect_token_keyboard():
    buttons = [
            [types.InlineKeyboardButton(text="➡️🔑 Подключить токен", callback_data="token_connect")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="callback_start")]
    ]
    return return_keyboard(buttons)