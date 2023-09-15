import opengate as gate
import opengate_core as g4
from box import Box

from ..GateObjects import GateObject
from ..helpers import warning, fatal
from .PhysicsListManager import PhysicsListManager


class PhysicsManager(GateObject):
    """
    Everything related to the physics (lists, cuts, etc.) should be here.
    """

    # names for particle cuts
    cut_particle_names = {
        "gamma": "gamma",
        "electron": "e-",
        "positron": "e+",
        "proton": "proton",
    }

    user_info_defaults = {}
    user_info_defaults["physics_list_name"] = (
        "QGSP_BERT_EMV",
        {"doc": "Name of the Geant4 physics list. "},
    )
    user_info_defaults["global_production_cuts"] = (
        Box([("all", None)] + [(pname, None) for pname in cut_particle_names]),
        {
            "doc": "Dictionary containing the production cuts (range) for gamma, electron, positron, proton. Option 'all' overrides individual cuts."
        },
    )
    user_info_defaults["apply_cuts"] = (
        True,
        {"doc": "Flag to turn of cuts 'on the fly'. Still under development in Gate."},
    )
    user_info_defaults["energy_range_min"] = (
        None,
        {
            "doc": "Minimum energy for secondary particle production. If None, physics list default is used."
        },
    )
    user_info_defaults["energy_range_max"] = (
        None,
        {
            "doc": "Maximum energy for secondary particle production. If None, physics list default is used."
        },
    )
    user_info_defaults["user_limits_particles"] = (
        Box(
            [
                ("all", False),
                ("all_charged", True),
                ("gamma", False),
                ("electron", False),
                ("positron", False),
                ("proton", False),
            ]
        ),
        {
            "doc": "Switch on (True) or off (False) UserLimits, e.g. step limiter, for individual particles. Default: Step limiter is applied to all charged particles (in accordance with G4 default)."
        },
    )
    user_info_defaults["em_parameters"] = (
        Box(
            [
                ("fluo", None),
                ("auger", None),
                ("auger_cascade", None),
                ("pixe", None),
                ("deexcitation_ignore_cut", None),
            ]
        ),
        {"doc": "Switches on (True) or off (False) Geant4's EM parameters."},
    )
    user_info_defaults["em_switches_world"] = (
        Box([("deex", None), ("auger", None), ("pixe", None)]),
        {
            "doc": "Switch on/off EM parameters in the world region.",
            "expose_items": False,
        },
    )

    # user_info_defaults["enable_decay"] = (
    #     False,
    #     {"doc": "Will become obsolete after PR 187 is merged. "},
    # )

    user_info_defaults["special_physics_constructors"] = (
        Box(
            [
                (spc, False)
                for spc in PhysicsListManager.special_physics_constructor_classes
            ]
        ),
        {
            "doc": "Special physics constructors to be added to the physics list, e.g. G4Decay, G4OpticalPhysics. "
        },
    )

    def __init__(self, simulation, *args, **kwargs):
        super().__init__(name="physics_manager", *args, **kwargs)

        # Keep a pointer to the current simulation
        self.simulation = simulation
        self.physics_list_manager = PhysicsListManager(self, name="PhysicsListManager")

        # dictionary containing all the region objects
        # key=region_name, value=region_object
        self.regions = {}
        # Dictionary to quickly find the region to which a volume is associated.
        # This dictionary is updated by the region's associate_volume method.
        # Do not update manually!
        # key=volume_name, value=region=object
        # NB: It is well-defined because each volume has only one region.
        self.volumes_regions_lut = {}

    def __str__(self):
        s = ""
        for k, v in self.user_info.items():
            s += f"{k}: {v}\n"
        return s

    def __getstate__(self):
        if self.simulation.verbose_getstate:
            gate.warning("Getstate PhysicsManager")

        dict_to_return = dict([(k, v) for k, v in self.__dict__.items()])
        dict_to_return["physics_list_manager"] = None
        return dict_to_return

    def __setstate__(self, d):
        self.__dict__ = d
        self.physics_list_manager = PhysicsListManager(self, name="PhysicsListManager")

    def _simulation_engine_closing(self):
        """This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.

        """
        # Region contain references to G4 objects, so they need to close
        for r in self.regions.values():
            r.close()

    def dump_available_physics_lists(self):
        return self.physics_list_manager.dump_info_physics_lists()

    def dump_info_physics_lists(self):
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

    @property
    def enable_decay(self):
        """Properties to quickly enable decay.

        Note that setting enable_decay to False means that the physics list
        default is used, i.e. it does not forcefully remove
        G4DecayPhysics from the physics list.
        """

        switch1 = self.special_physics_constructors["G4DecayPhysics"]
        switch2 = self.special_physics_constructors["G4RadioactiveDecayPhysics"]
        if switch1 is True and switch2 is True:
            return True
        elif switch1 is False and switch2 is False:
            return False
        else:
            fatal(
                f"Inconsistent G4Decay constructors: G4DecayPhysics = {switch1}, G4RadioactiveDecayPhysics = {switch2}."
            )

    @enable_decay.setter
    def enable_decay(self, value):
        self.special_physics_constructors["G4DecayPhysics"] = value
        self.special_physics_constructors["G4RadioactiveDecayPhysics"] = value

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
