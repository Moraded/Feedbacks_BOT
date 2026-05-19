import logging
import os
from pythonjsonlogger import jsonlogger


def setup_logger():
	os.makedirs("logs", exist_ok=True)

	root = logging.getLogger()
	root.setLevel(logging.INFO)
	root.handlers.clear()

	file_handler = logging.FileHandler("logs/bot.log")
	file_handler.setFormatter(jsonlogger.JsonFormatter(fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

	root.addHandler(file_handler)
	root.addHandler(console_handler)