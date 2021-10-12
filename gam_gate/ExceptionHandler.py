import gam_g4 as g4
import gam_gate as gam


class ExceptionHandler(g4.GamExceptionHandler):
    """
    Geant4 exception handler. Inherit form GamExceptionHandler
    The function 'Notify' will be called by G4 when an exception occurs.
    Should be created after initialization.
    Will be automatically stoed in the G4 stateManager
    """

    def Notify(self, originOfException, exceptionCode, severity, description):
        s = f'G4Exception origin: {originOfException}\n'
        s += f'G4Exception code: {exceptionCode}\n'
        s += f'G4Exception severity: {severity}\n'
        s += f'G4Exception: {description}'
        if severity == g4.FatalException or severity == g4.FatalErrorInArgument:
            gam.fatal(s)
        gam.warning(s)
        return False
