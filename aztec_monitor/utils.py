"""Utility helpers shared across the application."""

from __future__ import annotations

import csv
import functools
import random
import time
from sys import stderr
from typing import Callable

from loguru import logger

from user_data.config import settings

from .models import CsvAccount

LOG_OUTPUT = "./log/main.log"
LOG_ROTATION = "50 MB"

logger.level("BLUE", no=25, color="<blue>", icon="[•]")
logger.level("YELLOW", no=28, color="<yellow>", icon="[•]")
logger.level("CYAN", no=28, color="<cyan>", icon="[•]")
logger.level("MAGENTA", no=28, color="<magenta>", icon="[•]")


def _make_level_logger(level: str) -> Callable:
    def log(self, message, *args, **kwargs):
        return self.log(level, message, *args, **kwargs)

    return log


logger.__class__.blue = _make_level_logger("BLUE")  # type: ignore[attr-defined]
logger.__class__.yellow = _make_level_logger("YELLOW")  # type: ignore[attr-defined]
logger.__class__.cyan = _make_level_logger("CYAN")  # type: ignore[attr-defined]
logger.__class__.magenta = _make_level_logger("MAGENTA")  # type: ignore[attr-defined]


def add_logger(log_output: str = LOG_OUTPUT, log_rotation: str = LOG_ROTATION) -> None:
    """Configure loguru to log both to stderr and file."""

    logger.remove()
    logger.add(
        stderr,
        format=(
            "<bold><blue>{time:HH:mm:ss}</blue> | "
            "<level>{extra[icon]}</level> | "
            "<level>{message}</level></bold>"
        ),
        filter=lambda record: record.update(
            extra={
                "icon": {
                    "SUCCESS": "[+]",
                    "INFO": "[•]",
                    "WARNING": "[!]",
                    "ERROR": "[-]",
                    "BLUE": "[•]",
                    "YELLOW": "[•]",
                    "CYAN": "[•]",
                    "MAGENTA": "[•]",
                }.get(record["level"].name, record["level"].name)
            }
        )
        or True,
    )
    logger.add(sink=log_output, rotation=log_rotation)


def read_csv(csv_path: str) -> list[CsvAccount]:
    """Read validator accounts from ``csv_path``."""

    accounts: list[CsvAccount] = []
    with open(csv_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            accounts.append(
                CsvAccount(
                    id=int(row["id"]),
                    address=row["address"],
                    ip=row["ip"],
                    port=row["port"],
                    note=row.get("note"),
                )
            )
    return accounts


def retry(module: str, max_retries: int = settings.monitoring.requests.retries):
    """Retry decorator with jitter."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - defensive logging
                    attempts += 1
                    try:
                        logger.warning(
                            f"#{kwargs['acc'].id} | [{module}] retry #{attempts}/{max_retries}. error: {exc}"
                        )
                    except Exception:
                        logger.warning(f"[{module}] retry #{attempts}/{max_retries}. error: {exc}")
                    time.sleep(random.uniform(1, 5))
            return False

        return wrapper

    return decorator


def sleep_in_range(
    sec_from: float,
    sec_to: float,
    acc_id: int | None = None,
    log: str | None = None,
) -> None:
    """Sleep for a random number of seconds between the provided bounds."""

    if sec_from > sec_to:
        raise ValueError("invalid sleep range: lower bound greater than upper bound")

    sleep_time = random.uniform(sec_from, sec_to)
    if log:
        if acc_id:
            logger.info(f"#{acc_id} | sleep {round(sleep_time, 2)} sec | {log}.")
        else:
            logger.info(f"sleep {round(sleep_time, 2)} sec | {log}.")
    time.sleep(sleep_time)
