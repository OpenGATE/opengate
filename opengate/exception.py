import inspect
import colored

import opengate_core as g4
from .logger import log


class GateDeprecationError(Exception):
    """Raise this if a deprecated feature is used.
    Provide the user with information on how to update their code.
    """


class GateFeatureUnavailableError(Exception):
    """Raise this if a feature is used that is (currently) unavailable.
    Ideally, provide the user with information about alternatives.
    Can be used as temporary workaround during refactorings.
    """


class GateImplementationError(Exception):
    """Raise this if a feature is used that is (currently) unavailable.
    Ideally, provide the user with information about alternatives.
    Can be used as temporary workaround during refactorings.
    """


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
    raise Exception(s)


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
