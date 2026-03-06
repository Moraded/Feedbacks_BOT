import requests
import logging


logger = logging.getLogger(__name__)

def get_seller_info(WB_TOKEN):
    try:
        url = "https://common-api.wildberries.ru/api/v1/seller-info"
        headers = {"Authorization": WB_TOKEN}
        r = requests.get(url, headers=headers)
        return r.json()
    except (requests.exceptions.RequestException, KeyError, ValueError):
        logger.exception("Ошибка обработки данных о продавце")
        return None


def get_wb_feedbacks(WB_TOKEN):
    try:
        url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks"
        headers = {"Authorization": WB_TOKEN}
        params = {"isAnswered": "false", "take": 100, "skip": 0}
        r = requests.get(url, headers=headers, params=params)
        return r.json()["data"]["feedbacks"]
    except (requests.exceptions.RequestException, KeyError, ValueError):
        logger.exception("Ошибка при получении отзывов от ВБ")
        return None


def send_answer_to_wb(feedback_id, answer_text, WB_TOKEN):
    try:
        url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks/answer"
        headers = {"Authorization": WB_TOKEN}
        data = {"id": feedback_id, "text": answer_text}
        r = requests.post(url, headers=headers, json=data)
        return r.status_code == 204
    except (requests.exceptions.RequestException, KeyError, ValueError):
        logger.exception("Ошибка отправки отзывов на ВБ")
        return None


def check_token(WB_TOKEN):
    try:  
        url = "https://feedbacks-api.wildberries.ru/ping"
        headers = {"Authorization": WB_TOKEN}
        r = requests.get(url, headers=headers)
        return r.status_code
    except requests.exceptions.RequestException:
        logger.exception("Ошибка при проверке токена")
        return None
