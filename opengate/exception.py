import inspect
import os
import sys

import colored
import opengate_core as g4

from .logger import logger


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


class GateJobsBackendError(Exception):
    """Raise this when a split-job execution backend fails or rejects its options."""


class GateSplitError(Exception):
    """Raise this when a simulation merge operation fails."""


class GateMergeError(Exception):
    """Raise this when a simulation merge operation fails."""


class GateUserError(Exception):
    """Raise this for an error of the user (e.g. a wrong parameter or an
    existing output) with a message that says what to do. If it is not caught,
    only the message is printed, without the Python traceback (see
    _gate_excepthook); set the environment variable OPENGATE_TRACEBACK=1 to
    get the traceback.
    """


color_error = colored.fore("red") + colored.style("bold")
color_warning = colored.fore("orange_1")
color_ok = colored.fore("light_blue")


def fatal(s):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    ss = f"Fatal in {caller.filename} line {caller.lineno}"
    logger.critical(ss)
    logger.critical(s)
    raise Exception(s)


def _gate_excepthook(exc_type, exc_value, exc_traceback):
    """Print only the message of an uncaught GateUserError (the traceback
    is not useful to the user), the other exceptions as usual."""
    if issubclass(exc_type, GateUserError) and not os.environ.get("OPENGATE_TRACEBACK"):
        logger.critical(str(exc_value))
        return
    _previous_excepthook(exc_type, exc_value, exc_traceback)


_previous_excepthook = sys.excepthook
sys.excepthook = _gate_excepthook


def warning(s):
    logger.warning(s)


def raise_except(s):
    # s = colored.stylize(s, color_error)
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
