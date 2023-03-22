import opengate as gate
import opengate_core as g4
from box import Box

from opengate import log
from ..Decorators import requires_fatal


class Region(gate.GateObject):
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
            + "\t* min_range\n"
        },
    )
    user_info_defaults["production_cuts"] = (
        Box(dict([(p, None) for p in gate.particle_names_gate2g4.keys()])),
        {
            "doc": "\tProduction cut per particle to be applied in volumes associated with this region.\n"
            + "\tShould be provided as key:value pair as: `particle_name` (string) : `cut_value` (numerical)\n"
            + "\tThe following particle names are allowed:\n"
            + "".join([f"\t* {p}\n" for p in gate.PhysicsManager.cut_particle_names])
        },
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.physics_manager = None
        self.physics_engine = None

        self.volumes = {}
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
    # def associate_volume(self, volume, propagate_to_children=False):
    #     volume_name = volume.name
    #     if volume_name not in self.volumes.keys():
    #         self.volumes[volume_name] = volume
    #     else:
    #         gate.fatal(f'This volume {volume_name} is already associated with this region.')
    #     if propagate_to_children is True:
    #         self.root_logical_volumes['volume_name'] = volume

    @requires_fatal("physics_manager")
    def associate_volume(self, volume_name, propagate_to_children=False):
        if volume_name in self.volumes.keys():
            gate.fatal(
                f"This volume {volume_name} is already associated with this region."
            )
        self.volumes[volume_name] = None
        if propagate_to_children is True:
            self.root_logical_volumes["volume_name"] = None
        self.physics_manager.volumes_regions_lut[volume_name] = self

    @requires_fatal("physics_engine")
    def initialize(self):
        """This methods wraps around all initialization methods of this class.

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
            gate.fatal("No physics_engine defined.")
        for vname in self.volumes.keys():
            self.volumes[
                vname
            ] = self.physics_engine.simulation_engine.volume_engine.get_volume(vname)
        for vname in self.root_logical_volumes.keys():
            self.root_logical_volumes[
                vname
            ] = self.physics_engine.simulation_engine.volume_engine.get_volume(vname)

    def initialize_g4_region(self):
        if self._g4_region_initialized is True:
            gate.fatal("g4_region already initialized.")

        rs = g4.G4RegionStore.GetInstance()
        self.g4_region = rs.FindOrCreateRegion(self.name)
        log.info(f"Created g4_region {self.g4_region.GetName()} in Region {self.name}")

        if self.g4_user_limits is not None:
            log.info(f"Set G4UserLimits in region {self.g4_region.GetName()}")
            self.g4_region.SetUserLimits(self.g4_user_limits)

        if self.g4_production_cuts is not None:
            self.g4_region.SetProductionCuts(self.g4_production_cuts)

        for vol in self.root_logical_volumes.values():
            self.g4_region.AddRootLogicalVolume(vol.g4_logical_volume, True)

        for lv in self.volumes.values():
            lv.g4_logical_volume.SetRegion(self.g4_region)
            log.info(
                f"Set region {lv.g4_logical_volume.GetRegion().GetName()} in logical volume {lv.g4_logical_volume.GetName()}"
            )

        self._g4_region_initialized = True

    def initialize_g4_production_cuts(self):
        if self._g4_production_cuts_initialized is True:
            gate.fatal("g4_production_cuts already initialized.")
        for pname, cut in self.production_cuts.items():
            if cut is not None:
                if self.g4_production_cuts is None:
                    self.g4_production_cuts = g4.G4ProductionCuts()
                self.g4_production_cuts.SetProductionCut(cut, pname)

        self._g4_production_cuts_initialized = True

    def initialize_g4_user_limits(self):
        if self._g4_user_limits_initialized is True:
            gate.fatal("g4_user_limits already initialized.")

        # check if any user limits have been set
        # if not, it is not necessary to create g4 objects
        if all([(ul is None) for ul in self.user_limits.values()]) is True:
            self._g4_user_limits_initialized = True
            return

        self.g4_user_limits = g4.G4UserLimits()

        if self.user_limits["max_step_size"] is None:
            self.g4_user_limits.SetMaxAllowedStep(gate.FLOAT_MAX)
        else:
            self.g4_user_limits.SetMaxAllowedStep(self.user_limits["max_step_size"])

        if self.user_limits["max_track_length"] is None:
            self.g4_user_limits.SetUserMaxTrackLength(gate.FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTrackLength(
                self.user_limits["max_track_length"]
            )

        if self.user_limits["max_time"] is None:
            self.g4_user_limits.SetUserMaxTime(gate.FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTime(self.user_limits["max_time"])

        if self.user_limits["min_ekine"] is None:
            self.g4_user_limits.SetUserMinEkine(0.0)
        else:
            self.g4_user_limits.SetUserMinEkine(self.user_limits["min_ekine"])

        if self.user_limits["min_range"] is None:
            self.g4_user_limits.SetUserMinRange(0.0)
        else:
            self.g4_user_limits.SetUserMinRange(self.user_limits["min_range"])

        self._g4_user_limits_initialized = True
