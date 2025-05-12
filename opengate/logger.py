from loguru import logger
import os
import sys

# Ensure UTF-8 encoding is used
os.environ["PYTHONUTF8"] = "1"
if sys.getdefaultencoding() != "utf-8":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# Remove the default logger configuration
logger.remove()

# configure logger
logger.level("DEBUG", color="<green>")
logger.level("DEBUG", icon="🐞 ")
logger.level("INFO", icon="")
logger.level("INFO", color="<green>")
logger.level("NONE", no=100, color="")
logger.level("WARNING", icon="⚠️ ")
logger.level("CRITICAL", icon="☠️ ")

# default log level of loguru
DEBUG = 10
INFO = 20
WARNING = 30
CRITICAL = 50
NONE = 100

# default log level for running_verbose_level
RUN = 20
EVENT = 50


def log_level(log_handler_id):
    handler_config = logger._core.handlers.get(log_handler_id)
    return handler_config.levelno
