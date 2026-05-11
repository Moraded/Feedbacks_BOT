import aiohttp
import logging


logger = logging.getLogger(__name__)

async def get_seller_info(wb_token: str, session: aiohttp.ClientSession) -> dict[str, str] | None:
    try:
        url = "https://common-api.wildberries.ru/api/v1/seller-info"
        headers = {"Authorization": wb_token}
        async with session.get(url, headers=headers) as response:
            return await response.json()
    except (aiohttp.ClientError, KeyError, ValueError):
        logger.exception("❌ Ошибка обработки данных о продавце")
        return None
    

async def get_wb_feedbacks(wb_token: str, session: aiohttp.ClientSession) -> list | None:
    try:
        url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks"
        headers = {"Authorization": wb_token}
        params = {"isAnswered": "false", "take": 100, "skip": 0}
        async with session.get(url, headers=headers, params=params) as response:
            r = await response.json()
            return r["data"]["feedbacks"]
    except (aiohttp.ClientError, KeyError, ValueError):
        logger.exception(f"❌ Ошибка при получении отзывов от ВБ: {r}")
        return None


async def send_answer_to_wb(feedback_id: str, answer_text: str, wb_token: str, session: aiohttp.ClientSession) -> bool | None:
    try:
        url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks/answer"
        headers = {"Authorization": wb_token}
        data = {"id": feedback_id, "text": answer_text}
        async with session.post(url, headers=headers, json=data) as response:
            return response.status == 204
    except (aiohttp.ClientError, KeyError, ValueError):
        logger.exception("❌ Ошибка отправки отзыва на ВБ")
        return None


async def check_token(wb_token: str, session: aiohttp.ClientSession) -> int | None:
    try:  
        url = "https://feedbacks-api.wildberries.ru/ping"
        headers = {"Authorization": wb_token}
        async with session.get(url, headers=headers) as response:
            return response.status
    except (aiohttp.ClientError, KeyError, ValueError):
        logger.exception("❌ Ошибка при проверке токена")
        return None
