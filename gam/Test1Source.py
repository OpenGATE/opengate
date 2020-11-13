import gam
import gam_g4 as g4


class Test1Source(gam.SourceBase):
    """
    FIXME. Not needed. DEBUG.
    """

    type_name = 'Test1'

    def __init__(self, name):
        print('py Test1Source const ')
        gam.SourceBase.__init__(self, name, g4.GamTest1Source())
