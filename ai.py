import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import logging
from system_prompt import SYSTEM_PROMPT


logger = logging.getLogger(__name__)

load_dotenv()

aitunnel = AsyncOpenAI(api_key=os.getenv("AITUNNEL_KEY"), base_url="https://api.aitunnel.ru/v1/", timeout=60.0, max_retries=2)

async def generate_answer(feedback: dict, review_number: int) -> str | None:
  try:
    #Генерирует ответ через AITUNNEL на основе отзыва и системного промпта
    review_text = feedback.get("text") or ""
    pros = feedback.get("pros") or ""
    cons = feedback.get("cons") or ""
    full_text = f"{review_text} {pros} {cons}".strip()

    product = feedback["productDetails"]["productName"]
    rating = feedback["productValuation"]
    name = feedback["userName"]
    color = feedback.get("color", "")
    size = feedback["productDetails"].get("size", "")
    status_map = {
      "buyout": "выкуплен",
      "rejected": "отказали",
      "returned": "возврат",
      "notSpecified": "статус не присвоен",
    }
    orderstatus = feedback.get('orderStatus')
    orderstatus = status_map.get(orderstatus, "статус не присвоен")

    prompt = f"""Отзыв от {name}. Оценка: {rating}/5.
Товар: {product}, цвет: {color}, размер: {size}.
Текст отзыва: {full_text}, Статус заказа: {orderstatus}, номер отзыва: {review_number}"""

    response = await aitunnel.chat.completions.create(
        model="deepseek-v3.2-exp",
        max_tokens=768,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
  except openai.APITimeoutError:
    logger.exception(f"Таймаут при обработке отзыва #{review_number}, пропускаем отзыв.")
  except openai.APIError:
    logger.exception("Ошибка при генерации ответа на отзыв")
    return None