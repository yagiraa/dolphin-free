from loguru import logger
from sys import stderr


# LOGGING SETTING
file_log = 'logs/log.log'
logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{level: <8}</level> | <cyan>{line}</cyan> - <white>{message}</white>")
logger.add(file_log, format="<white>{time:HH:mm:ss}</white> | <level>{level: <8}</level> | <cyan>{line}</cyan> - <white>{message}</white>")

# API URL SETTINGS
LOCAL_API_BASE_URL = 'http://127.0.0.1:5000'
REMOTE_API_BASE_URL = 'https://dolphin-anty-api.com'
REMOTE_SYNC_API_BASE_URL = 'https://sync.dolphin-anty-api.com'
