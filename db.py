import sqlite3

def init_db():
    #База данных пользователей
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, token TEXT)')
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
        token = None
    return token


def register_user(user_id):
  conn = sqlite3.connect('users.db')
  cursor = conn.cursor()
  cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user_id, ""))
  conn.commit()
  cursor.close()
  conn.close()


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
    return False

def reset_token(user_id):
  try:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET token = ? WHERE user_id = ?", ("", user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True
  except sqlite3.Error:
    return False
