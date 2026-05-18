#Хранилище сгенерированного ответа, нужен для кнопок Отправить/Редактировать
pending_reviews: dict[str, dict] = {} # {feedback_id: {текст}}
#Хранилище отзывов для разных режимов ответов на отзывы
user_feedbacks: dict[int, list[dict]] = {} # {user_id: [список отзывов]}
#Индекс для отслеживания текущего отзыва в ручном режиме
user_review_index: dict[int, int] = {} # {user_id: int}
#Флаг для остановки ответов в автоматизированом режиме
flag_stop_reply_auto: dict[int, bool] = {} # {user_id: bool}

def get_current_feedbacks(user_id):
	return user_feedbacks[user_id][user_review_index[user_id]]

def save_pending_review(fb, answer):
	pending_reviews[fb["id"]] = {"answer": answer, "feedback_id": fb["id"]}

def next_review(user_id):
	user_review_index[user_id] += 1

def clear_session(user_id):
	user_feedbacks.pop(user_id, None)
	user_review_index.pop(user_id, None)