import opengate as gate
import opengate_core as g4
from box import Box

from ..helpers import warning
from .PhysicsListManager import PhysicsListManager


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

        self.physics_list_manager = PhysicsListManager(self, name="PhysicsListManager")

        # default values
        self._default_parameters()

        # dictionary containing all the region objects
        # key=region_name, value=region_object
        self.regions = {}

        # Dictionary to quickly find the region to which a volume is associated.
        # This dictionary is updated by the region's associate_volume method.
        # Do not update manually!
        # key=volume_name, value=region=object
        # NB: It is well-defined because each volume has only one region.
        self.volumes_regions_lut = {}

    def __del__(self):
        if self.simulation.verbose_destructor:
            gate.warning("Deleting PhysicsManager")

    def __str__(self):
        s = f"{self.user_info.physics_list_name} Decay: {self.user_info.enable_decay}"
        return s

    def __getstate__(self):
        if self.simulation.verbose_getstate:
            gate.warning("Getstate PhysicsManager")
        self.__dict__["physics_list_manager"] = None
        return self.__dict__

    def _default_parameters(self):
        ui = self.user_info
        # keep the name to be able to come back to default
        self.default_physic_list = "QGSP_BERT_EMV"
        ui.physics_list_name = self.default_physic_list
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

    def _simulation_engine_closing(self):
        """This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.

        """
        # Region contain references to G4 objects, so they need to close
        for r in self.regions.values():
            r.close()

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
        return self.physics_list_manager.dump_info_physics_lists()

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

    def create_region(self, name):
        if name in self.regions.keys():
            gate.fatal("A region with this name already exists.")
        self.regions[name] = gate.Region(name=name)
        self.regions[name].physics_manager = self
        return self.regions[name]

    def find_or_create_region(self, volume_name):
        if volume_name not in self.volumes_regions_lut.keys():
            region = self.create_region(volume_name + "_region")
            region.associate_volume(volume_name)
        else:
            region = self.volumes_regions_lut[volume_name]
        return region

    # keep 'old' function name for compatibility
    def set_cut(self, volume_name, particle_name, value):
        warning(
            "Deprecation warning: User PhysicsManager.set_production_cuts() instead of PhysicsManager.set_cuts()"
        )
        self.set_production_cut(volume_name, particle_name, value)

    # New name, more specific
    def set_production_cut(self, volume_name, particle_name, value):
        if volume_name == self.simulation.world.name:
            self.global_production_cuts[particle_name] = value
        else:
            region = self.find_or_create_region(volume_name)
            region.production_cuts[particle_name] = value

    # set methods for the user_info parameters
    # logic: every volume with user_infos must be associated
    # with a region. If it does not yet have one, created it.
    # Outlook: These setter methods might be linked to properties
    # implemented in a future version of the Volume class
    def set_max_step_size(self, volume_name, max_step_size):
        region = self.find_or_create_region(volume_name)
        region.user_limits["max_step_size"] = max_step_size

    def set_max_track_length(self, volume_name, max_track_length):
        region = self.find_or_create_region(volume_name)
        region.user_limits["max_track_length"] = max_track_length

    def set_min_ekine(self, volume_name, min_ekine):
        region = self.find_or_create_region(volume_name)
        region.user_limits["min_ekine"] = min_ekine

    def set_max_time(self, volume_name, max_time):
        region = self.find_or_create_region(volume_name)
        region.user_limits["max_time"] = max_time

    def set_min_range(self, volume_name, min_range):
        region = self.find_or_create_region(volume_name)
        region.user_limits["min_range"] = min_range

    def set_user_limits_particles(self, particle_names):
        if not isinstance(particle_names, (list, set, tuple)):
            particle_names = list([particle_names])
        for pn in list(particle_names):
            # try to get current value to check if particle_name is eligible
            try:
                _ = self.user_info.user_limits_particles[pn]
            except KeyError:
                gate.fatal(
                    f"Found unknown particle name '{pn}' in set_user_limits_particles(). Eligible names are "
                    + ", ".join(list(self.user_info.user_limits_particles.keys()))
                    + "."
                )
            self.user_info.user_limits_particles[pn] = True
