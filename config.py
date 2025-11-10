import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))

    SMTP_TIMEOUT = 10
    MAX_CONCURRENT_VERIFICATIONS = 50
    CACHE_TTL = 86400

    DNS_SERVERS = ['8.8.8.8', '1.1.1.1', '8.8.4.4']

    FROM_EMAIL = 'bookf826@gmail.com'

    RATE_LIMIT_PER_MINUTE = 100


config = Config()