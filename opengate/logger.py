import logging
import colorlog
import sys

# https://github.com/borntyping/python-colorlog
# The available color names are black,
# red, green, yellow, blue, purple, cyan and white.


class CustomFormatter(colorlog.ColoredFormatter):
    """
    The level name (INFO, DEBUG etc) is only printed if not equal to INFO
    """

    def format(self, record):
        # Check the log level and adjust the message format accordingly
        if record.levelname == "INFO":
            self._style._fmt = "%(log_color)s%(message)s%(reset)s"
        else:
            self._style._fmt = (
                "%(log_color)s%(levelname)-8s%(reset)s%(log_color)s%(message)s"
            )

        return super().format(record)


# main format
formatter = CustomFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s%(log_color)s%(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
)


# set output message to standard output
log_handler = colorlog.StreamHandler(sys.stdout)

# install default handler format
log_handler.setFormatter(formatter)

# get main log object
global_log = colorlog.getLogger("opengate_logger")
global_log.propagate = False
if not global_log.hasHandlers():
    global_log.addHandler(log_handler)

# default log level
# global_log.setLevel(logging.INFO)
global_log.setLevel(0)


def print_logger_hierarchy(logger_name):
    logger = logging.getLogger(logger_name)
    while logger:
        print(f"Logger: {logger.name}")
        print(f"  Level: {logger.level}")
        print(f"  Handlers: {logger.handlers}")
        # Move to the parent logger
        if logger.parent and logger.parent is not logger:
            logger = logger.parent
        else:
            break


# shorter for level
NONE = 0
DEBUG = logging.DEBUG
INFO = logging.INFO
RUN = 20
EVENT = 50
