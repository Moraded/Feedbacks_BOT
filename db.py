import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_db():
    #База данных пользователей
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    cursor.close()
    conn.close()
    
    #База данных кабинетов и токенов
    conn = sqlite3.connect('cabinets.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS cabinets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, token TEXT, seller_name TEXT, brand_name TEXT, is_active INTEGER DEFAULT 0)')
    conn.commit()
    cursor.close()
    conn.close()
    

def get_user_cabinets(user_id):
    try:


def get_active_token(user_id):
    try:
        conn = sqlite3.connect('cabinets.db')
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM cabinets WHERE user_id = ? and is_active = 1", (user_id,))
        result = cursor.fetchone()
        token = result[0] if result else None
        cursor.close()
        conn.close()
    except (sqlite3.Error, TypeError):
        logger.exception("Ошибка при получения токена из базы или новый пользователь")
        token = None
    return token


def register_user(user_id):
  try:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при занесении пользователя в базу данных")
    return False


#def save_seller_info(seller_name, user_id, token):
  try:
    conn = sqlite3.connect('cabinets.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE cabinets SET seller_name = ? WHERE user_id = ? and token = ? and brand_name = ?", (seller_name, user_id, token,))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при сохранении имени продавца в базу")
    return False

def get_user_seller_name(token):
    try:
        conn = sqlite3.connect('cabinets.db')
        cursor = conn.cursor()
        cursor.execute("SELECT seller_name FROM cabinets WHERE token = ?", (token))
        seller_name = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except (sqlite3.Error, TypeError):
        logger.exception("Ошибка при получении имени продавца из базы")
        seller_name = None
    return seller_name


def add_cabinet(user_id, token, seller_name, brand_name):
  try:
    conn = sqlite3.connect('cabinets.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cabinets WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] == 0:
      is_active = 1
    else:
      is_active = 0
    cursor.execute("INSERT INTO cabinets (user_id, token, seller_name, brand_name, is_active) VALUES (?, ?, ?, ?, ?)", (user_id, token, seller_name, brand_name, is_active))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при сохранении токена")
    return False

def reset_token(user_id, token):
  try:
    conn = sqlite3.connect('cabinets.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cabinets WHERE user_id = ? AND token = ?", (user_id, token))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    logger.exception("Ошибка при сбросе токена")
    return False