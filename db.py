import aiosqlite
import logging

logger = logging.getLogger(__name__)


class DatabaseBot:
  def __init__(self, db_path: str):
    self.db_path = db_path
    self.db = None

  async def connect(self):
    self.db = await aiosqlite.connect(self.db_path)
    self.db.row_factory = aiosqlite.Row
    await self._create_tables()

  async def _create_tables(self):
    await self.db.execute("""
CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)""")
    await self.db.execute("""
CREATE TABLE IF NOT EXISTS cabinets (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user_id INTEGER,
                          token TEXT,
                          seller_name TEXT,
                          brand_name TEXT,
                          is_active INTEGER DEFAULT 0,
                          UNIQUE(user_id, token))""")
    await self.db.commit()
  async def close(self):
    await self.db.close()

  async def get_user_cabinets(self, user_id: int) -> str | None:
    try:
      async with self.db.execute(
        "SELECT id, seller_name, brand_name, is_active FROM cabinets WHERE user_id = ?", (user_id,)
      ) as cursor:
        result = await cursor.fetchall()
    except (aiosqlite.Error, TypeError):
      logger.exception("❌ Ошибка при получении списка кабинетов")
      result = None
    return result


  async def switch_cabinet(self, user_id, id):
    try:
      async with self.db.execute("UPDATE cabinets SET is_active = 0 WHERE user_id = ? AND is_active = 1", (user_id,)):
        async with self.db.execute("UPDATE cabinets SET is_active = 1 WHERE id = ? AND user_id = ?", (id, user_id)):
          await self.db.commit()
          return True
    except (aiosqlite.Error, TypeError):
      logger.exception("❌ Ошибка при обновлении статуса кабинета")
      return False


  async def get_active_token(self, user_id):
    try:
      async with self.db.execute("SELECT token FROM cabinets WHERE user_id = ? and is_active = 1", (user_id,)) as cursor:
        result = await cursor.fetchone()
        token = result[0] if result else None
    except (aiosqlite.Error, TypeError):
      logger.exception("❌ Ошибка при получении токена из базы или новый пользователь")
      token = None
    return token
  
  async def register_user(self, user_id):
    try:
      async with self.db.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,)):
        await self.db.commit()
        return True
    except (aiosqlite.Error, TypeError):
      logger.exception("❌ Ошибка при занесении пользователя в базу данных")
      return False

  async def get_user_seller_name(self, token):
    try:
      async with self.db.execute("SELECT seller_name FROM cabinets WHERE token = ?", (token,)) as cursor:
        row = await cursor.fetchone()
        seller_name = row[0] if row else None
    except (aiosqlite.Error, TypeError):
      logger.exception("Ошибка при получении имени продавца из базы")
      seller_name = None
    return seller_name


  async def add_cabinet(self, user_id, token, seller_name, brand_name):
    try:
      async with self.db.execute("UPDATE cabinets SET is_active = 0 WHERE user_id = ?", (user_id,)):
        async with self.db.execute("INSERT INTO cabinets (user_id, token, seller_name, brand_name, is_active) VALUES (?, ?, ?, ?, ?)", (user_id, token, seller_name, brand_name, 1)):
          await self.db.commit()
          return True
    except aiosqlite.IntegrityError as e:
      logger.exception(f"Ошибка дублирования данных или иная: {e}")
      return "duplicate"
    except aiosqlite.Error:
      logger.exception("Ошибка при сохранении токена")
      return False


  async def reset_token(self, user_id, token):
    try:
      async with self.db.execute("DELETE FROM cabinets WHERE user_id = ? AND token = ?", (user_id, token)):
        await self.db.commit()
        return True
    except aiosqlite.Error:
      logger.exception("Ошибка при сбросе токена")
      return False
