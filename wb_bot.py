import asyncio
import aiohttp
import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from db import DatabaseBot
from handlers.admin import router as admin_router
from handlers.cabinets import router as cabinets_router
from handlers.reviews import router as reviews_router
from handlers.start import router as start_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

async def main():
    logger.info("Бот запущен")
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(cabinets_router)
    dp.include_router(reviews_router)
    database = DatabaseBot("bot.db")
    await database.connect()
    dp["db"] = database
    session = aiohttp.ClientSession()
    dp["session"] = session
    ai_semaphore = asyncio.Semaphore(5)
    dp["ai_semaphore"] = ai_semaphore
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await session.close()
        await database.close()
if __name__ == "__main__":
    asyncio.run(main())