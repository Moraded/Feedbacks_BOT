import requests

def get_wb_feedbacks(WB_TOKEN):
    try:
        url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks"
        headers = {"Authorization": WB_TOKEN}
        params = {"isAnswered": "false", "take": 125, "skip": 0}
        r = requests.get(url, headers=headers, params=params)
        print(f"WB status code get feedbacks: {r.status_code}")
        return r.json()["data"]["feedbacks"]
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return None


def send_answer_to_wb(feedback_id, answer_text, WB_TOKEN):
    try:
        url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks/answer"
        headers = {"Authorization": WB_TOKEN}
        data = {"id": feedback_id, "text": answer_text}
        r = requests.post(url, headers=headers, json=data)
        print(f"WB status code: {r.status_code}")
        return r.status_code == 204
    except (requests.exceptions.RequestException, KeyError, ValueError):
        print(f"WB status code: {r.status_code}")
        return None


def check_token(WB_TOKEN):
    try:  
        url = "https://feedbacks-api.wildberries.ru/ping"
        headers = {"Authorization": WB_TOKEN}
        r = requests.get(url, headers=headers)
        print(f"WB token check status code: {r.status_code}")
        return r.status_code
    except requests.exceptions.RequestException:
        return None
