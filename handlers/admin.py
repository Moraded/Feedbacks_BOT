from aiogram import Router, types
from aiogram.filters import Command
from db import DatabaseBot
import os

router = Router()

ADMIN_ID = os.getenv("ADMIN_ID")

@router.message(Command("broadcast"))
async def broadcast_handler(message: types.Message, db: DatabaseBot):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(" ", 1)
    text = parts[1].strip() if len(parts) > 1 else "" 
    if not text:
        await message.answer("❌ Текст для рассылки не указан. Используйте формат: /broadcast Ваш текст") 
        return

    users = await db.get_all_users()

    success, failed = 0, 0
    for user_id in users:
        try:
            await message.bot.send_message(user_id, text)
            success += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Рассылка завершена! Успешно: {success}, Не доставлено: {failed}")