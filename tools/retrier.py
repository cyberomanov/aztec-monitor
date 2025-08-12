import functools
import random
import time

from loguru import logger

from user_data import config


def retry(module: str, max_retries: int = config.max_retries):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    try:
                        logger.warning(f"#{kwargs['acc'].id} | [{module}] retry #{attempts}/{max_retries}. error: {e}")
                    except:
                        logger.warning(f"[{module}] retry #{attempts}/{max_retries}. error: {e}")

                    time.sleep(random.randint(1, 5))

            return False

        return wrapper

    return decorator
