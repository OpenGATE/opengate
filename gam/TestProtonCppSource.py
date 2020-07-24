from box import Box

import gam  # needed for gam_setup
import gam_g4 as g4


class TestProtonCppSource(g4.GamTestProtonSource):
    """
    FIXME. Not needed. DEBUG.
    """

    def __init__(self, source):
        """
        TODO
        """
        g4.GamTestProtonSource .__init__(self)