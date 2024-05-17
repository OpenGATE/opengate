import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units


class ChemistryActor(g4.GateChemistryActor, ActorBase):
    """ """

    type_name = "ChemistryActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)

        user_info.output = "output.root"
        user_info.timestep_model = "IRT"
        user_info.reactions = []
        user_info.default_reactions = True
        user_info.end_time = 1 * g4_units.s
        user_info.time_bins_count = 10
        user_info.molecule_counter_verbose = 0

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateChemistryActor.__init__(self, user_info.__dict__)

    def __str__(self):
        u = self.user_info
        s = f'ChemistryActor "{u.name}": dim={u.size} spacing={u.spacing} {u.output} tr={u.translation}'
        return s

    def __getstate__(self):
        # superclass getstate
        ActorBase.__getstate__(self)
        return self.__dict__

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)

    def StartSimulationAction(self):
        pass

    def EndSimulationAction(self):
        pass


class ChemistryLongTimeActor(g4.GateChemistryLongTimeActor, ActorBase):
    """ """

    type_name = "ChemistryLongTimeActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)

        user_info.output = "output.root"
        user_info.timestep_model = "IRT"
        user_info.reactions = []
        user_info.end_time = 1 * g4_units.s
        user_info.time_bins_count = 10
        user_info.molecule_counter_verbose = 0

        user_info.pH = 7
        user_info.scavengers = []

        user_info.dose_cutoff = 0

        user_info.reset_scavenger_for_each_beam = False

        # TODO remove
        user_info.boundary_size = [
            0.8 * g4_units.um,
            0.8 * g4_units.um,
            0.8 * g4_units.um,
        ]

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateChemistryLongTimeActor.__init__(self, user_info.__dict__)

    def __str__(self):
        u = self.user_info
        s = f'ChemistryLongTimeActor "{u.name}": dim={u.size} spacing={u.spacing} {u.output} tr={u.translation}'
        return s

    def __getstate__(self):
        # superclass getstate
        ActorBase.__getstate__(self)
        return self.__dict__

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)

    def StartSimulationAction(self):
        pass

    def EndSimulationAction(self):
        pass
