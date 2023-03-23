import opengate as gate
import opengate_core as g4
from box import Box


class PhysicsManager:
    """
    Everything related to the physics (lists, cuts etc) should be here.
    """

    # names for particle cuts
    cut_particle_names = {
        "gamma": "gamma",
        "electron": "e-",
        "positron": "e+",
        "proton": "proton",
    }

    def __init__(self, simulation):
        # Keep a pointer to the current simulation
        self.simulation = simulation
        # user options
        self.user_info = gate.PhysicsUserInfo(self.simulation)
        # NK: the PhysicsUserInfo constructor
        # expects the simulation object, not the PhysicsManager
        # maybe the reason for the segfault (see __del__)?

        # default values
        self._default_parameters()

        # dictionary containing all the region objects
        # key=region_name, value=region_object
        self.regions = {}

        # Dictionary to quickly find the region to which a volume is associated.
        # This dictionary is updated by the region's associate_volume method.
        # Do not update manually!
        # key=volume_name, value=region=object
        # NB: It is well defined because each volume has only one region.
        self.volumes_regions_lut = {}

    def __del__(self):
        # not really clear, but it seems that we should delete user_info here
        # if not seg fault (sometimes) at the end
        # print("del PhysicsManager (then del user info)")
        # del self.user_info
        # NK: Don't think this is necessary. See comment in __init__
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
        # ui.production_cuts.world = Box()
        # ui.production_cuts.world.gamma = -1  # -1 means = will be the phys list default
        # ui.production_cuts.world.proton = -1
        # ui.production_cuts.world.electron = -1
        # ui.production_cuts.world.positron = -1
        # ui.production_cuts.world.propagate_to_daughters = True
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

    # define this as property for convenience
    # will become one automatically after refactoring into GateObject
    @property
    def global_production_cuts(self):
        return self.user_info.global_production_cuts

    @property
    def physics_list_name(self):
        return self.user_info.physics_list_name

    @physics_list_name.setter
    def physics_list_name(self, name):
        self.user_info.physics_list_name = name

    def dump_available_physics_lists(self):
        factory = g4.G4PhysListFactory()
        s = (
            f"Phys List:     {factory.AvailablePhysLists()}\n"
            f"Phys List EM:  {factory.AvailablePhysListsEM()}\n"
            f"Phys List add: {gate.available_additional_physics_lists}"
        )
        return s

    # alias for back-compatibility
    def dump_cuts(self):
        gate.warning(
            "Deprecation warning: Old version dump_cuts called. Update implementation to use dump_production_cuts()."
        )
        return self.dump_production_cuts()

    def dump_production_cuts(self):
        s = "*** Production cuts for World: ***\n"
        for k, v in self.user_info.global_production_cuts.items():
            s += f"{k}: {v}\n"
        if len(self.regions.keys()) > 0:
            s += f"*** Production cuts per regions ***\n"
            for region in self.regions.values():
                s += f"In region {region.name}:\n"
                s += region.dump_production_cuts()
        else:
            s += "*** No cuts per region defined. ***\n"
        return s

    # def set_cut(self, volume_name, particle_name, value):
    #     cuts = self.user_info.production_cuts
    #     if volume_name not in cuts:
    #         s = f'Cannot find the volume "{volume_name}" to define its cut.'
    #         gate.fatal(s)
    #     if particle_name == "all":
    #         cuts[volume_name]["gamma"] = value
    #         cuts[volume_name]["electron"] = value
    #         cuts[volume_name]["positron"] = value
    #         cuts[volume_name]["proton"] = value
    #         return
    #     if particle_name not in cuts[volume_name]:
    #         s = f'Cannot find the particle named "{particle_name}" to define its cut in the volume "{volume_name}".'
    #         gate.fatal(s)
    #     cuts[volume_name][particle_name] = value

    def create_region(self, region_name):
        if region_name in self.regions.keys():
            gate.fatal("A region with this name already exists.")
        self.regions[region_name] = gate.Region(name=region_name)
        self.regions[region_name].physics_manager = self
        return self.regions[region_name]

    def find_or_create_region(self, volume_name, propagate_to_daughters=False):
        if volume_name not in self.volumes_regions_lut.keys():
            region = self.create_region(volume_name + "_region")
            region.associate_volume(volume_name, propagate_to_daughters)
        else:
            region = self.volumes_regions_lut[volume_name]
        return region

    # keep 'old' function name for compatibility
    def set_cut(self, volume_name, particle_name, value):
        self.set_production_cut(volume_name, particle_name, value)

    # New name, more specific
    def set_production_cut(
        self, volume_name, particle_name, value, propagate_to_daughters=False
    ):
        region = self.find_or_create_region(volume_name, propagate_to_daughters)
        region.production_cuts[particle_name] = value

    # set methods for the user_info parameters
    # logic: every volume with user_infos must be associated
    # with a region. If it does not yet have one, created it.
    # Outlook: These setter methods might be linked to properties
    # implemented in a future version of the Volume class
    def set_max_step_size(
        self, volume_name, max_step_size, propagate_to_daughters=False
    ):
        region = self.find_or_create_region(volume_name, propagate_to_daughters)
        region.user_limits["max_step_size"] = max_step_size

    def set_max_track_length(
        self, volume_name, max_track_length, propagate_to_daughters=False
    ):
        region = self.find_or_create_region(volume_name, propagate_to_daughters)
        region.user_limits["max_track_length"] = max_track_length

    def set_min_ekine(self, volume_name, min_ekine, propagate_to_daughters=False):
        region = self.find_or_create_region(volume_name, propagate_to_daughters)
        region.user_limits["min_ekine"] = min_ekine

    def set_max_time(self, volume_name, max_time, propagate_to_daughters=False):
        region = self.find_or_create_region(volume_name, propagate_to_daughters)
        region.user_limits["max_time"] = max_time

    def set_min_range(self, volume_name, min_range, propagate_to_daughters=False):
        region = self.find_or_create_region(volume_name, propagate_to_daughters)
        region.user_limits["min_range"] = min_range

    def set_user_limits_particles(self, volume_name, particle_names):
        region = self.find_or_create_region(volume_name)
        region.user_limits["particles"] = particle_names
