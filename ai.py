import anthropic
import os

claude = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

SYSTEM_PROMPT = """Ты — менеджер на Wildberries. 
Пиши короткие тёплые ответы на отзывы покупателей. 2-3 предложения. 
Без шаблонности, живым языком. Учитывай название товара, оценку и имя покупателя.
Если отзыв негативный — извинись и предложи связаться для решения проблемы.
Не используй эмодзи."""

def generate_answer(feedback):
  try:
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
  except anthropic.APIError:
    return None