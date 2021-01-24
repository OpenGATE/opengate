import gam
import gam_g4 as g4
import logging
import colorlog
from gam import log
from box import Box


class PhysicsManager:
    """
    FIXME TODO
    """

    def __init__(self, simulation):
        # Keep a pointer to the current simulation
        self.simulation = simulation
        # main g4 physic list
        self.g4_physic_list = None
        # user settings
        self.default_physic_list = 'QGSP_BERT_EMZ'
        self.name = self.default_physic_list

    def __del__(self):
        pass

    def initialize(self):
        print('Phys list init')
        # Select the Physic List
        factory = g4.G4PhysListFactory()
        if not factory.IsReferencePhysList(self.name):
            s = f'Cannot find the physic list : {self.name}\n' \
                f'Known list are : {factory.AvailablePhysLists()}\n' \
                f'With EM : {factory.AvailablePhysListsEM()}\n' \
                f'Default is {self.default_physic_list}\n' \
                f'Help : https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html'
            gam.fatal(s)
        self.g4_physic_list = factory.GetReferencePhysList(self.name)
        # Cuts
        # FIXME
