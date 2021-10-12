import logging
import colorlog
import sys

# https://github.com/borntyping/python-colorlog
# The available color names are black,
# red, green, yellow, blue, purple, cyan and white.

# main format
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(log_color)s%(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'NONE': 'cyan',
        'DEBUG': 'cyan',
        'INFO': 'green'
    },
    secondary_log_colors={},
    style='%'
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
