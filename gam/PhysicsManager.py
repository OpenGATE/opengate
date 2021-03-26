import gam
import gam_g4 as g4
from box import Box
from gam.VolumeManager import __world_name__
from anytree import LevelOrderIter

cut_particle_names = {'gamma': 'gamma', 'electron': 'e-', 'positron': 'e+', 'proton': 'proton'}


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
        self.name = None
        self.decay = None
        self.g4_em_parameters = g4.G4EmParameters.Instance()
        self.production_cuts = Box()
        self.energy_range_min = None
        self.energy_range_max = None
        self.apply_cuts = None
        # G4
        self.g4_decay = None
        self.g4_radioactive_decay = None
        self.g4_cuts_by_regions = []
        # default values
        self._default_parameters()

    def __del__(self):
        pass

    def __str__(self):
        s = f'{self.name} Decay: {self.decay}'
        return s

    def _default_parameters(self):
        self.default_physic_list = 'QGSP_BERT_EMV'
        self.name = self.default_physic_list
        self.decay = False
        mm = gam.g4_units('mm')
        self.production_cuts.world = Box()
        self.production_cuts.world.gamma = -1  # -1 means = will be the phys list default
        self.production_cuts.world.proton = -1
        self.production_cuts.world.electron = -1
        self.production_cuts.world.positron = -1
        self.production_cuts.world.propagate_to_daughters = True
        keV = gam.g4_units('keV')
        GeV = gam.g4_units('GeV')
        self.energy_range_min = 0.250 * keV
        self.energy_range_max = 0.5 * GeV
        self.apply_cuts = True

    def initialize(self):
        self.initialize_physics_list()
        self.initialize_decay()
        self.initialize_em_options()
        # self.initialize_cuts()

    def dump_available_physics_lists(self):
        factory = g4.G4PhysListFactory()
        s = f'Phys List:     {factory.AvailablePhysLists()}\n' \
            f'Phys List EM:  {factory.AvailablePhysListsEM()}\n' \
            f'Phys List add: {gam.available_additional_physics_lists}'
        return s

    def dump_cuts(self):
        if self.simulation.is_initialized:
            return self.dump_cuts_initialized()
        s = ''
        for c in self.production_cuts:
            s += f'{c} : {self.production_cuts[c]}\n'
        return s

    def dump_cuts_initialized(self):
        s = ''
        if not self.apply_cuts:
            s = f'Apply cuts is FALSE: following cuts are NOT used.\n'
        lvs = g4.G4LogicalVolumeStore.GetInstance()
        for i in range(lvs.size()):
            lv = lvs.Get(i)
            region = lv.GetRegion()
            cuts = region.GetProductionCuts()
            s += f'{region.GetName()}: '
            for p in cut_particle_names:
                v = cuts.GetProductionCut(cut_particle_names[p])
                s += f'{p} {v} mm '
            s += '\n'
        # remove last line break
        return s[:-1]

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
        # range
        pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
        pct.SetEnergyRange(self.energy_range_min, self.energy_range_max)
        # inherit production cuts
        self.propagate_cuts_to_child()
        # global cuts
        self.g4_em_parameters.SetApplyCuts(self.apply_cuts)
        if not self.apply_cuts:
            s = f'No production cuts (apply_cuts is False)'
            gam.warning(s)
            gam.fatal('Not implemented: currently it crashes when apply_cuts is False. To be continued ...')
            return
        # production cuts by region
        for region in self.production_cuts:
            self.set_region_cut(region)

    def propagate_cuts_to_child(self):
        tree = self.simulation.volume_manager.volumes_tree
        pc = self.production_cuts
        # loop on the tree, level order
        for node in LevelOrderIter(tree[__world_name__]):
            if not node.parent:
                # this is the world, do nothing
                continue
            # get the user cuts for this region
            if node.name in pc:
                cuts = pc[node.name]
            else:
                gam.fatal(f'Cannot find region {node.name} in the cuts list: {pc}')
            # get the cuts for the parent
            if node.parent.name in pc:
                pcuts = pc[node.parent.name]
            else:
                gam.fatal(f'Cannot find parent region {node.parent.name} in the cuts list: {pc}')
            for p in cut_particle_names:
                # set the cut for the current region like the parent
                # but only if it was not set by user
                if p not in cuts:
                    if p in pcuts:
                        cuts[p] = pcuts[p]
                    else:
                        # special case when the parent=world, with default cuts
                        cuts[p] = -1
                        pcuts[p] = -1

    def set_region_cut(self, region):
        # get the values for this region
        cuts_values = self.production_cuts[region]
        # special case for world region
        if region == __world_name__:
            region = 'DefaultRegionForTheWorld'
        rs = g4.G4RegionStore.GetInstance()
        reg = rs.GetRegion(region, True)
        if not reg:
            l = ''
            for i in range(rs.size()):
                l += f'{rs.Get(i).GetName()} '
            s = f'Cannot find the region name "{region}". Knowns regions are: {l}'
            gam.fatal(s)
        # set the cuts for the region
        cuts = None
        for p in cuts_values:
            if p not in cut_particle_names:
                s = f'Cuts error : I find "{p}" while cuts can only be set for: {cut_particle_names.keys()}'
                gam.fatal(s)
            if not cuts:
                cuts = g4.G4ProductionCuts()
            a = cut_particle_names[p]
            v = cuts_values[p]
            if type(v) != int and type(v) != float:
                gam.fatal(f'The cut value must be a number, while it is {v} in {cuts_values}')
            if v < 0:
                v = self.g4_physic_list.GetDefaultCutValue()
            cuts.SetProductionCut(v, a)
        reg.SetProductionCuts(cuts)
        # keep the cut object to prevent deletion
        self.g4_cuts_by_regions.append(cuts)
