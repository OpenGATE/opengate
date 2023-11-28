import opengate_core as g4


class Bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class UIsessionVerbose(g4.G4UIsession):
    """
    Print Geant4 Verbose with color
    """

    def ReceiveG4cout(self, coutString):
        print(f"{Bcolors.OKBLUE}{coutString}", end="")
        return 0

    def ReceiveG4cerr(self, cerrString):
        print(f"{Bcolors.WARNING}{cerrString}", end="")
        return 0


class UIsessionSilent(g4.G4UIsession):
    """
    TODO
    """

    def ReceiveG4cout(self, coutString):
        # print('HERE ', coutString)
        return 0

    def ReceiveG4cerr(self, cerrString):
        # print('HERE ', cerrString)
        return 0
