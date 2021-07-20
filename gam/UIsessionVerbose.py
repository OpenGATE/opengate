import gam_g4 as g4


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class UIsessionVerbose(g4.G4UIsession):
    """
    Print Geant4 Verbose with color
    """

    def __del__(self):
        pass

    def ReceiveG4cout(self, coutString):
        print(f'{bcolors.OKBLUE}{coutString}', end='')
        return 0

    def ReceiveG4cerr(self, cerrString):
        print(f'{bcolors.WARNING}{cerrString}', end='')
        return 0
