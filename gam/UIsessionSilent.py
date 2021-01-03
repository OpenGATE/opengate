import gam_g4 as g4


class UIsessionSilent(g4.G4UIsession):
    """
    TODO
    """

    def __del__(self):
        # need a destructor, if not seg fault at the end
        print('UIsessionSilent destructor')
        pass

    def ReceiveG4cout(self, coutString):
        # print('HERE ', coutString)
        return 0

    def ReceiveG4cerr(self, cerrString):
        # print('HERE ', cerrString)
        return 0
