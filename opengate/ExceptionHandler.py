import opengate_core as g4
import opengate as gate


class ExceptionHandler(g4.GateExceptionHandler):
    """
    Geant4 exception handler. Inherit form GateExceptionHandler
    The function 'Notify' will be called by G4 when an exception occurs.
    Should be created after initialization.
    Will be automatically stoed in the G4 stateManager
    """

    def Notify(self, originOfException, exceptionCode, severity, description):
        s = f"G4Exception origin: {originOfException}\n"
        s += f"G4Exception code: {exceptionCode}\n"
        s += f"G4Exception severity: {severity}\n"
        s += f"G4Exception: {description}"
        if severity == g4.FatalException or severity == g4.FatalErrorInArgument:
            gate.fatal(s)
        gate.warning(s)
        return False
