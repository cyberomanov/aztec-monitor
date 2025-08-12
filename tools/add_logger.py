from sys import stderr

from loguru import logger

LOG_OUTPUT = "./log/main.log"
LOG_ROTATION = "50 MB"

logger.level("BLUE", no=25, color="<blue>", icon="[•]")
logger.level("YELLOW", no=28, color="<yellow>", icon="[•]")
logger.level("CYAN", no=28, color="<cyan>", icon="[•]")
logger.level("MAGENTA", no=28, color="<magenta>", icon="[•]")


def blue(self, message, *args, **kwargs):
    return self.log("BLUE", message, *args, **kwargs)


def yellow(self, message, *args, **kwargs):
    return self.log("YELLOW", message, *args, **kwargs)


def cyan(self, message, *args, **kwargs):
    return self.log("CYAN", message, *args, **kwargs)


def magenta(self, message, *args, **kwargs):
    return self.log("MAGENTA", message, *args, **kwargs)


logger.__class__.blue = blue
logger.__class__.yellow = yellow
logger.__class__.cyan = cyan
logger.__class__.magenta = magenta


def add_logger(log_output: str = LOG_OUTPUT, log_rotation: str = LOG_ROTATION):
    logger.remove()

    logger.add(
        stderr,
        format="<bold><blue>{time:HH:mm:ss}</blue> | "
               "<level>{extra[icon]}</level> | "
               "<level>{message}</level></bold>",
        filter=lambda record: record.update(extra={
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
        }) or True
    )
    logger.add(sink=log_output, rotation=log_rotation)
