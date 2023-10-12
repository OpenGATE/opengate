from box import Box

import opengate_core as g4

from .exception import warning, fatal
from .definitions import FLOAT_MAX
from .decorators import requires_fatal

from .base import GateObject


# names for particle cuts
cut_particle_names = {
    "gamma": "gamma",
    "electron": "e-",
    "positron": "e+",
    "proton": "proton",
}


# translation from particle names used in Gate
# to particles names used in Geant4
def translate_particle_name_gate2G4(name):
    """Convenience function to translate from names
    used in Gate to those in G4, if necessary.
    Concerns e.g. 'electron' -> 'e-'
    """
    try:
        return cut_particle_names[name]
    except KeyError:
        return name


class UserLimitsPhysics(g4.G4VPhysicsConstructor):
    """
    Class to be registered to physics list.

    It is essentially a refined version of StepLimiterPhysics which considers the user's
    particles choice of particles to which the step limiter should be added.

    """

    def __init__(self):
        """Objects of this class are created via the PhysicsEngine class.
        The user should not create objects manually.

        """
        g4.G4VPhysicsConstructor.__init__(self, "UserLimitsPhysics")
        self.physics_engine = None

        self.g4_step_limiter_storage = {}
        self.g4_special_user_cuts_storage = {}

        print("UserLimitsPhysics.__init__")

    def close(self):
        self.g4_step_limiter_storage = None
        self.g4_special_user_cuts_storage = None

    @requires_fatal("physics_engine")
    def ConstructParticle(self):
        """Needs to be defined because C++ base class declares this as purely virtual member."""
        pass

    @requires_fatal("physics_engine")
    def ConstructProcess(self):
        """Overrides method from G4VPhysicsConstructor
        that is called when the physics list is constructed.

        """
        ui = self.physics_engine.user_info_physics_manager

        particle_keys_to_consider = []
        # 'all' overrides individual settings
        if ui.user_limits_particles["all"] is True:
            particle_keys_to_consider = list(ui.user_limits_particles.keys())
        else:
            keys_to_exclude = ("all", "all_charged")
            particle_keys_to_consider = [
                p
                for p, v in ui.user_limits_particles.items()
                if v is True and p not in keys_to_exclude
            ]

        if len(particle_keys_to_consider) == 0:
            warning(
                "user_limits_particles is False for all particles. No tracking cuts will be applied. Use Simulation.set_user_limits_particles()."
            )

        # translate to Geant4 particle names
        particles_to_consider = [
            translate_particle_name_gate2G4(k) for k in particle_keys_to_consider
        ]

        for particle in g4.G4ParticleTable.GetParticleTable().GetParticleList():
            add_step_limiter = False
            add_user_special_cuts = False
            p_name = str(particle.GetParticleName())

            if p_name in particles_to_consider:
                add_step_limiter = True
                add_user_special_cuts = True

            # this reproduces the logic of the Geant4's G4StepLimiterPhysics class
            if (
                ui.user_limits_particles["all_charged"] is True
                and particle.GetPDGCharge() != 0
            ):
                add_step_limiter = True

            if add_step_limiter is True or add_user_special_cuts is True:
                pm = particle.GetProcessManager()
                if add_step_limiter is True:
                    # G4StepLimiter for the max_step_size cut
                    g4_step_limiter = g4.G4StepLimiter("StepLimiter")
                    pm.AddDiscreteProcess(g4_step_limiter, 1)
                    # store limiter and cuts in lists to
                    # to avoid garbage collection after exiting the methods
                    self.g4_step_limiter_storage[p_name] = g4_step_limiter
                if add_user_special_cuts is True:
                    # G4UserSpecialCuts for the other cuts
                    g4_user_special_cuts = g4.G4UserSpecialCuts("UserSpecialCut")
                    pm.AddDiscreteProcess(g4_user_special_cuts, 1)
                    self.g4_special_user_cuts_storage[p_name] = g4_user_special_cuts


class Region(GateObject):
    """FIXME: Documentation of the Region class."""

    user_info_defaults = {}
    user_info_defaults["user_limits"] = (
        Box(
            {
                "max_step_size": None,
                "max_track_length": None,
                "min_ekine": None,
                "max_time": None,
                "min_range": None,
            }
        ),
        {
            "doc": "\tUser limits to be applied during tracking. \n"
            + "\tFIXME: Will be applied to all particles specified in the \n"
            + "\tlist under the `particles` keyword, if eligible.\n"
            + "\tUse `all` to apply tracking limits to all eligible particles.\n"
            + "\tThe following limits can be set:\n"
            + "\t* max_step_size\n"
            + "\t* max_track_length\n"
            + "\t* min_ekine\n"
            + "\t* max_time\n"
            + "\t* min_range\n",
            # expose_items=True means that the user_limits are also accessible directly
            # via Region.max_step_size, not only via Region.user_limits.max_step_size
            # that's more convenient for the user
            "expose_items": True,
        },
    )
    user_info_defaults["production_cuts"] = (
        Box(dict([(p, None) for p in cut_particle_names.keys()])),
        {
            "doc": "\tProduction cut per particle to be applied in volumes associated with this region.\n"
            + "\tShould be provided as key:value pair as: `particle_name` (string) : `cut_value` (numerical)\n"
            + "\tThe following particle names are allowed:\n"
            + "".join([f"\t* {p}\n" for p in cut_particle_names])
        },
    )
    user_info_defaults["em_switches"] = (
        Box([("deex", None), ("auger", None), ("pixe", None)]),
        {
            "doc": "Switch on/off EM parameters in this region. If None, the corresponding value from the world region is used.",
            "expose_items": True,
        },
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # references to upper hierarchy level
        self.physics_manager = None
        self.physics_engine = None

        # dictionaries to hold volumes to which this region is associated
        # self.volumes = {}
        self.root_logical_volumes = {}

        # g4_objects; will be created by resp. initialize_XXX() methods
        self.g4_region = None
        self.g4_user_limits = None
        self.g4_production_cuts = None

        # flags for private use
        self._g4_region_initialized = False
        self._g4_user_limits_initialized = False
        self._g4_production_cuts_initialized = False

    # this version will work when Volume inherits from GateObject
    # def associate_volume(self, volume):
    #     volume_name = volume.name
    #     if volume_name not in self.root_logical_volumes.keys():
    #         self.root_logical_volumes[volume_name] = volume
    #     else:
    #         fatal(f'This volume {volume_name} is already associated with this region.')

    def close(self):
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_region = None
        self.g4_user_limits = None
        self.g4_production_cuts = None

    def need_step_limiter(self):
        if self.user_info["user_limits"]["max_step_size"] is not None:
            return True
        else:
            return False

    def need_user_special_cut(self):
        if (
            self.user_info["user_limits"]["max_track_length"] is not None
            or self.user_info["user_limits"]["min_ekine"] is not None
            or self.user_info["user_limits"]["max_time"] is not None
            or self.user_info["user_limits"]["min_range"] is not None
        ):
            return True
        else:
            return False

    @requires_fatal("physics_manager")
    def associate_volume(self, volume):
        # Allow volume object to be passed and retrieve its name in that case
        try:
            volume_name = volume.name
        except AttributeError:
            volume_name = volume

        if volume_name in self.root_logical_volumes.keys():
            fatal(f"This volume {volume_name} is already associated with this region.")
        self.root_logical_volumes[volume_name] = None
        self.physics_manager.volumes_regions_lut[volume_name] = self

    def dump_production_cuts(self):
        s = ""
        for pname, cut in self.production_cuts.items():
            if cut is not None:
                s += f"{pname}: {cut}\n"
        return s

    @requires_fatal("physics_engine")
    def initialize(self):
        """
        This method wraps around all initialization methods of this class.

        It should be called from the physics_engine,
        after setting the self.physics_engine attribute.
        """
        self.initialize_volume_dictionaries()
        self.initialize_g4_production_cuts()
        self.initialize_g4_user_limits()
        self.initialize_g4_region()

    # This method is currently necessary because the actual volume objects
    # are only created at some point during initialization
    @requires_fatal("physics_engine")
    def initialize_volume_dictionaries(self):
        if self.physics_engine is None:
            fatal("No physics_engine defined.")
        for vname in self.root_logical_volumes.keys():
            self.root_logical_volumes[
                vname
            ] = self.physics_engine.simulation_engine.volume_engine.get_volume(vname)

    def initialize_g4_region(self):
        if self._g4_region_initialized is True:
            fatal("g4_region already initialized.")

        rs = g4.G4RegionStore.GetInstance()
        self.g4_region = rs.FindOrCreateRegion(self.user_info.name)

        if self.g4_user_limits is not None:
            self.g4_region.SetUserLimits(self.g4_user_limits)

        # if self.g4_production_cuts is not None:
        self.g4_region.SetProductionCuts(self.g4_production_cuts)

        for vol in self.root_logical_volumes.values():
            self.g4_region.AddRootLogicalVolume(vol.g4_logical_volume, True)
            vol.g4_logical_volume.SetRegion(self.g4_region)

        self._g4_region_initialized = True

    def initialize_g4_production_cuts(self):
        self.user_info = Box(self.user_info)

        if self._g4_production_cuts_initialized is True:
            fatal("g4_production_cuts already initialized.")
        if self.g4_production_cuts is None:
            self.g4_production_cuts = g4.G4ProductionCuts()

        # 'all' overrides individual cuts per particle
        try:
            cut_for_all = self.user_info["production_cuts"]["all"]
        except KeyError:
            cut_for_all = None
        if cut_for_all is not None:
            for pname in self.user_info["production_cuts"].keys():
                if pname == "all":
                    continue
                g4_pname = translate_particle_name_gate2G4(pname)
                self.g4_production_cuts.SetProductionCut(cut_for_all, g4_pname)
        else:
            for pname, cut in self.user_info["production_cuts"].items():
                if pname == "all":
                    continue
                # translate to G4 names, e.g. electron -> e+
                g4_pname = translate_particle_name_gate2G4(pname)
                if cut is not None:
                    self.g4_production_cuts.SetProductionCut(cut, g4_pname)
                # If no cut is specified by user for this particle,
                # set it to the value specified for the world region
                else:
                    global_cut = self.physics_engine.g4_physics_list.GetCutValue(
                        g4_pname
                    )
                    self.g4_production_cuts.SetProductionCut(global_cut, g4_pname)

        self._g4_production_cuts_initialized = True

    def initialize_g4_user_limits(self):
        if self._g4_user_limits_initialized is True:
            fatal("g4_user_limits already initialized.")

        # check if any user limits have been set
        # if not, it is not necessary to create g4 objects
        if all([(ul is None) for ul in self.user_info["user_limits"].values()]) is True:
            self._g4_user_limits_initialized = True
            return

        self.g4_user_limits = g4.G4UserLimits()

        if self.user_info["user_limits"]["max_step_size"] is None:
            self.g4_user_limits.SetMaxAllowedStep(FLOAT_MAX)
        else:
            self.g4_user_limits.SetMaxAllowedStep(
                self.user_info["user_limits"]["max_step_size"]
            )

        if self.user_info["user_limits"]["max_track_length"] is None:
            self.g4_user_limits.SetUserMaxTrackLength(FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTrackLength(
                self.user_info["user_limits"]["max_track_length"]
            )

        if self.user_info["user_limits"]["max_time"] is None:
            self.g4_user_limits.SetUserMaxTime(FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTime(
                self.user_info["user_limits"]["max_time"]
            )

        if self.user_info["user_limits"]["min_ekine"] is None:
            self.g4_user_limits.SetUserMinEkine(0.0)
        else:
            self.g4_user_limits.SetUserMinEkine(
                self.user_info["user_limits"]["min_ekine"]
            )

        if self.user_info["user_limits"]["min_range"] is None:
            self.g4_user_limits.SetUserMinRange(0.0)
        else:
            self.g4_user_limits.SetUserMinRange(
                self.user_info["user_limits"]["min_range"]
            )

        self._g4_user_limits_initialized = True

    def initialize_em_switches(self):
        # if all switches are None, nothing is to be set
        if any([v is not None for v in self.em_switches.values()]):
            values_to_set = {}
            for k, v in self.em_switches.items():
                if v is None:  # try to recover switch from world
                    values_to_set[k] = self.physics_manager.em_switches_world[k]
                    if values_to_set[k] is None:
                        fatal(
                            f"No value (True/False) provided for em_switch {k} in region {self.name} and no corresponding value set for the world either."
                        )
                else:
                    values_to_set[k] = v
            self.physics_engine.g4_em_parameters.SetDeexActiveRegion(
                self.name,
                values_to_set["deex"],
                values_to_set["auger"],
                values_to_set["pixe"],
            )
