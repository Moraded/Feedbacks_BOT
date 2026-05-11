#Хранилище отзывов для кнопок
pending_reviews: dict[str, dict] = {}
#Хранилище отзывов для режима ответов
user_feedbacks: dict[int, list[dict]] = {}
#Индекс для отслеживания текущего отзыва в ручном режиме
user_review_index: dict[int, int] = {}
#Флаг для остановки ответов в автоматизированом режиме
flag_stop_reply_auto: dict[int, bool] = {}