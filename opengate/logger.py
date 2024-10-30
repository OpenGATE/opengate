import logging
import colorlog
import sys

# https://github.com/borntyping/python-colorlog
# The available color names are black,
# red, green, yellow, blue, purple, cyan and white.


class CustomFormatter(colorlog.ColoredFormatter):
    """
    The levelname (INFO, DEBUG etc) is only printed if not equal to INFO
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
handler = colorlog.StreamHandler(sys.stdout)

# install default handler format
handler.setFormatter(formatter)

# get main log object
log = colorlog.getLogger(__name__)
log.addHandler(handler)

# default log level
log.setLevel(logging.INFO)

# shorter for level
NONE = 0
DEBUG = logging.DEBUG
INFO = logging.INFO
RUN = 20
EVENT = 50
