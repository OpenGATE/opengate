import gam
import gam_g4 as g4
import io


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
        self.default_physic_list = 'QGSP_BERT_EMV'
        self.name = self.default_physic_list
        self.decay = False
        self.g4_em_parameters = g4.G4EmParameters.Instance()
        # G4
        self.g4_decay = None
        self.g4_radioactive_decay = None

    def __del__(self):
        pass

    def __str__(self):
        s = f'Physics list name: {self.name} Decay: {self.decay}'
        return s

    def initialize(self):
        self.initialize_physics_list()
        self.initialize_decay()
        # self.initialize_em_options()
        # self.initialize_cuts()

    def dump_physics_list(self):
        factory = g4.G4PhysListFactory()
        s = f'Phys List: {factory.AvailablePhysLists()}\n' \
            f'Phys List EM: {factory.AvailablePhysListsEM()}\n' \
            f'Phys List add: {gam.available_additional_physics_lists}'
        return s

    def initialize_physics_list(self):
        # Select the Physic List: check if simple ones
        if self.name.startswith('G4'):
            self.g4_physic_list = gam.create_modular_physics_list(self.name)
        else:
            # If not, select the Physic List from the Factory
            factory = g4.G4PhysListFactory()
            if not factory.IsReferencePhysList(self.name):
                s = f'Cannot find the physic list : {self.name}\n' \
                    f'Known list are : {factory.AvailablePhysLists()}\n' \
                    f'With EM : {factory.AvailablePhysListsEM()}\n' \
                    f'Default is {self.default_physic_list}\n' \
                    f'Help : https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html'
                gam.fatal(s)
            self.g4_physic_list = factory.GetReferencePhysList(self.name)

    def initialize_decay(self):
        """
        G4DecayPhysics - defines all particles and their decay processes
        G4RadioactiveDecayPhysics - defines radioactiveDecay for GenericIon
        """
        if not self.decay:
            return
        # check if decay/radDecay already exist in the physics list
        # (keep p and pp in self to prevent destruction)
        self.g4_decay = self.g4_physic_list.GetPhysics('Decay')
        if not self.g4_decay:
            self.g4_decay = g4.G4DecayPhysics(1)
            self.g4_physic_list.RegisterPhysics(self.g4_decay)
        self.g4_radioactive_decay = self.g4_physic_list.GetPhysics('G4RadioactiveDecay')
        if not self.g4_radioactive_decay:
            self.g4_radioactive_decay = g4.G4RadioactiveDecayPhysics(1)
            self.g4_physic_list.RegisterPhysics(self.g4_radioactive_decay)

    def initialize_em_options(self):
        pass

    def initialize_cuts(self):
        # Cuts
        print('default cut value', self.g4_physic_list.GetDefaultCutValue())
        pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
        print('pct', pct)
        eV = gam.g4_units('eV')
        GeV = gam.g4_units('GeV')
        pct.SetEnergyRange(250 * eV, 100 * GeV)
        # Em Parameters
        # self.emp = g4.G4EmParameters.Instance()
        print(self.g4_em_parameters)
        self.g4_em_parameters.SetApplyCuts(True)
        print('cut done')
        # FIXME
