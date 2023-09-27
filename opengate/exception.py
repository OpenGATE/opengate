import inspect
import colored
import sys

import opengate_core as g4
from .logger import log


try:
    color_error = colored.fg("red") + colored.attr("bold")
    color_warning = colored.fg("orange_1")
    color_ok = colored.fg("green")
except AttributeError:
    # new syntax in colored>=1.5
    color_error = colored.fore("red") + colored.style("bold")
    color_warning = colored.fore("orange_1")
    color_ok = colored.fore("green")


def fatal(s):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    ss = f"(in {caller.filename} line {caller.lineno})"
    ss = colored.stylize(ss, color_error)
    log.critical(ss)
    s = colored.stylize(s, color_error)
    log.critical(s)
    sys.exit(-1)


def warning(s):
    s = colored.stylize(s, color_warning)
    log.warning(s)


def raise_except(s):
    s = colored.stylize(s, color_error)
    raise Exception(s)


class ExceptionHandler(g4.GateExceptionHandler):
    """
    Geant4 exception handler. Inherit form GateExceptionHandler
    The function 'Notify' will be called by G4 when an exception occurs.
    Should be created after initialization.
    Will be automatically stored in the G4 stateManager
    """

    def Notify(self, originOfException, exceptionCode, severity, description):
        s = f"G4Exception origin: {originOfException}\n"
        s += f"G4Exception code: {exceptionCode}\n"
        s += f"G4Exception severity: {severity}\n"
        s += f"G4Exception: {description}"
        if severity == g4.FatalException or severity == g4.FatalErrorInArgument:
            fatal(s)
        warning(s)
        return False
