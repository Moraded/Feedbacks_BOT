import asyncio
import anthropic
import requests
import os
import logging
import sqlite3
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramAPIError


logging.basicConfig(level=logging.INFO)
load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
claude = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

WB_TOKEN = os.getenv("WB_KEY_TOKEN")

SYSTEM_PROMPT = """Ты — менеджер на Wildberries. 
Пиши короткие тёплые ответы на отзывы покупателей. 2-3 предложения. 
Без шаблонности, живым языком. Учитывай название товара, оценку и имя покупателя.
Если отзыв негативный — извинись и предложи связаться для решения проблемы.
Не используй эмодзи."""

#Хранилище отзывов для кнопок
pending_reviews = {}

def init_db():
    #База данных пользователей
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, token TEXT)')
    conn.commit()
    cursor.close()
    conn.close()


def get_wb_feedbacks():
    #Получает неотвеченные отзывы с WB
    url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks"
    headers = {"Authorization": WB_TOKEN}
    params = {"isAnswered": "false", "take": 3, "skip": 0}
    r = requests.get(url, headers=headers, params=params)
    print(f"WB status code get feedbacks: {r.status_code}")
    return r.json()["data"]["feedbacks"]


def generate_answer(feedback):
    #Генерирует ответ через Claude
    review_text = feedback.get("text") or ""
    pros = feedback.get("pros") or ""
    cons = feedback.get("cons") or ""
    full_text = f"{review_text} {pros} {cons}".strip()

    product = feedback["productDetails"]["productName"]
    rating = feedback["productValuation"]
    name = feedback["userName"]
    color = feedback.get("color", "")
    size = feedback["productDetails"].get("size", "")

    prompt = f"""Отзыв от {name}. Оценка: {rating}/5.
Товар: {product}, цвет: {color}, размер: {size}.
Текст отзыва: {full_text}"""

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def send_answer_to_wb(feedback_id, answer_text):
    #Отправляем ответ на WB
    url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks/answer"
    headers = {"Authorization": WB_TOKEN}
    data = {"id": feedback_id, "text": answer_text}
    r = requests.post(url, headers=headers, json=data)
    print(f"WB status code: {r.status_code}")
    return r.status_code == 204


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (message.from_user.id, ""))
    conn.commit()
    cursor.close()
    conn.close()
    
    await message.answer(
        "Маяк Селлеров - бот для ответов на отзывы\n\n"
        "/reviews - загрузить неотвеченные отзывы"
    )
    await message.answer(f"ID: {message.from_user.id} записан в базу")


@dp.message(Command("reviews"))
async def cmd_reviews(message: types.Message):
    await message.answer("⌛ Загружаю ответы с WB...")
    try:
        feedbacks = get_wb_feedbacks()
    except requests.exceptions.RequestException:
        await message.answer("❌ Ошибка загрузки ответов с WB")
        return
    
    if not feedbacks:
        await message.answer("✅ Нет неотвеченных отзывов!")
        return
    
    await message.answer(f"Найдено отзывов: {len(feedbacks)}. Генерируем ответы...")

    for fb in feedbacks:
        try:
            answer = generate_answer(fb)
        except anthropic.APIError:
            await message.answer(f"Неудалось обработать отзыв {fb['id']}\n\n Переходим к следующему отзыву...")
            continue
        #Сохраняем для кнопок
        pending_reviews[fb["id"]] = {
            "answer": answer,
            "feedback_id": fb["id"]
        }

        #Формируем текст ВОТ ЗДЕСЬ ЕСТЬ ПРОБЛЕМА, НУЖНО СОЕДИНИТЬ PROS TEXT и ЕЩЕ
        review_text = f"{fb.get("text")} {fb.get("pros")} {fb.get("cons")}" or ""
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
        
@dp.callback_query(F.data.startswith("send_"))
async def on_send(callback: types.CallbackQuery):
    feedback_id = callback.data.replace("send_", "")
    review = pending_reviews.get(feedback_id)

    if not review:
        await callback.answer("Отзыв не найден")
        return
    try:
        success = send_answer_to_wb(feedback_id, review["answer"])
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