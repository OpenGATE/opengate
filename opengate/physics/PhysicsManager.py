import opengate as gate
import opengate_core as g4
from box import Box


class PhysicsManager:
    """
    Everything related to the physics (lists, cuts etc) should be here.
    """

    def __init__(self, simulation):
        # Keep a pointer to the current simulation
        self.simulation = simulation
        # user options
        self.user_info = gate.PhysicsUserInfo(self)
        # default values
        self._default_parameters()
        # names for particle cuts
        self.cut_particle_names = {
            "gamma": "gamma",
            "electron": "e-",
            "positron": "e+",
            "proton": "proton",
        }

    def __del__(self):
        # not really clear, but it seems that we should delete user_info here
        # if not seg fault (sometimes) at the end
        # print("del PhysicsManager (then del user info)")
        del self.user_info
        pass

    def __str__(self):
        s = f"{self.user_info.physics_list_name} Decay: {self.user_info.enable_decay}"
        return s

    def _default_parameters(self):
        ui = self.user_info
        # keep the name to be able to come back to default
        self.default_physic_list = "QGSP_BERT_EMV"
        ui.physics_list_name = self.default_physic_list
        ui.enable_decay = False
        ui.production_cuts.world = Box()
        ui.production_cuts.world.gamma = -1  # -1 means = will be the phys list default
        ui.production_cuts.world.proton = -1
        ui.production_cuts.world.electron = -1
        ui.production_cuts.world.positron = -1
        ui.production_cuts.world.propagate_to_daughters = True
        """
        FIXME Energy range not clear : does not work in mono-thread mode
        Ignored for the moment (keep them to None)
        """
        """
        eV = gate.g4_units('eV')
        keV = gate.g4_units('keV')
        GeV = gate.g4_units('GeV')
        ui.energy_range_min = 250 * eV
        ui.energy_range_max = 0.5 * GeV
        """
        ui.energy_range_min = None
        ui.energy_range_max = None
        ui.apply_cuts = True

    def dump_available_physics_lists(self):
        factory = g4.G4PhysListFactory()
        s = (
            f"Phys List:     {factory.AvailablePhysLists()}\n"
            f"Phys List EM:  {factory.AvailablePhysListsEM()}\n"
            f"Phys List add: {gate.available_additional_physics_lists}"
        )
        return s

    def dump_cuts(self):
        s = ""
        for c in self.user_info.production_cuts:
            s += f"{c} : {self.user_info.production_cuts[c]}\n"
        return s

    def set_cut(self, volume_name, particle_name, value):
        cuts = self.user_info.production_cuts
        if volume_name not in cuts:
            s = f'Cannot find the volume "{volume_name}" to define its cut.'
            gate.fatal(s)
        if particle_name == "all":
            cuts[volume_name]["gamma"] = value
            cuts[volume_name]["electron"] = value
            cuts[volume_name]["positron"] = value
            cuts[volume_name]["proton"] = value
            return
        if particle_name not in cuts[volume_name]:
            s = f'Cannot find the particle named "{particle_name}" to define its cut in the volume "{volume_name}".'
            gate.fatal(s)
        cuts[volume_name][particle_name] = value
