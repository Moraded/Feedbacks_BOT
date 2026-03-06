import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_db():
    #База данных пользователей
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, token TEXT, seller_name TEXT)')
    conn.commit()
    cursor.close()
    conn.close()


def get_user_token(user_id):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM users WHERE user_id = ?", (user_id,))
        token = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except (sqlite3.Error, TypeError):
        logger.exception("Ошибка при получения токена из базы")
        token = None
    return token


def register_user(user_id):
  try:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", (user_id, "", ""))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при занесении пользователя в базу данных")
    return False


def save_seller_info(seller_name, user_id):
  try:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET seller_name = ? WHERE user_id = ?", (seller_name, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при сохранении имени продавца в базу")
    return False

def get_user_seller_name(token):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT seller_name FROM users WHERE token = ?", (token,))
        seller_name = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except (sqlite3.Error, TypeError):
        logger.exception("Ошибка при получении имени продавца из базы")
        seller_name = None
    return seller_name


def save_token(user_id, token):
  try:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET token = ? WHERE user_id = ?", (token, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при сохранении токена")
    return False

def reset_token(user_id):
  try:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET token = ?, seller_name = ? WHERE user_id = ?", ("", "", user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при сбросе токена")
    return False