from loguru import logger

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
