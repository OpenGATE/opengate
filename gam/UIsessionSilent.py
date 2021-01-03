import gam_g4 as g4


class UIsessionSilent(g4.G4UIsession):
    """
    TODO
    """

    def __del__(self):
        pass

    def ReceiveG4cout(self, coutString):
        # print('HERE ', coutString)
        return 0

    def ReceiveG4cerr(self, cerrString):
        # print('HERE ', cerrString)
        return 0
