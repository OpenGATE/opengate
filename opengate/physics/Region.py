import opengate as gate
import opengate_core as g4
from box import Box


class Region(gate.GateObject):
    """FIXME: Documentation of the CutsAndLimitsRegion class."""

    user_info_defaults = {}
    user_info_defaults["tracking_cuts"] = (
        Box(
            {
                "max_step_size": None,
                "max_track_length": None,
                "min_ekine": None,
                "max_time": None,
                "min_range": None,
                "particles": [],
            }
        ),
        {
            "doc": "\tUser limits to be applied during tracking. \n"
            + "\tWill be applied to all particles specified in the \n"
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
        Box(),
        {
            "doc": "\tProduction cut per particle to be applied in volumes associated with this region.\n"
            + "\tShould be provided as key:value pair as: `particle_name` (string) : `cut_value` (numerical)\n"
            + "\tThe following particle names are allowed:\n"
            + "".join([f"\t* {p}\n" for p in gate.PhysicsManager.cut_particle_names])
        },
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(physics_manager, *args, **kwargs)

        self.physics_manager = physics_manager
        self.physics_engine = None

        self.volumes = {}
        self.root_logical_volumes = {}

        self.g4_region = None  # will be created by initialize()
        self.g4_user_limits = None
        self.g4_production_cuts = None

    # this version will work when Volume inherits from GateObject
    # def associate_volume(self, volume, propagate_to_children=False):
    #     volume_name = volume.name
    #     if volume_name not in self.volumes.keys():
    #         self.volumes[volume_name] = volume
    #     else:
    #         gate.fatal(f'This volume {volume_name} is already associated with this region.')
    #     if propagate_to_children is True:
    #         self.root_logical_volumes['volume_name'] = volume

    def associate_volume(self, volume_name, propagate_to_children=False):
        if volume_name not in self.volumes.keys():
            self.volumes[volume_name] = None
        else:
            gate.fatal(
                f"This volume {volume_name} is already associated with this region."
            )
        if propagate_to_children is True:
            self.root_logical_volumes["volume_name"] = None

    # This method is currently necessary because the actual volume objects
    # are only created at some point during initialization
    def initialize_volume_dictionaries(self):
        for vname in self.volumes.keys():
            self.volumes[
                vname
            ] = self.physics_engine.simulation_engine.volume_engine.get_volume(vname)
        for vname in self.root_logical_volumes.keys():
            self.volumes[
                vname
            ] = self.physics_engine.simulation_engine.volume_engine.get_volume(vname)

    def initialize_g4_region(self):
        if self.g4_region is not None:
            gate.fatal("g4_region already initialized.")
        if self.g4_user_limits is None:
            gate.fatal("g4_user_limits not initialized yet.")

        rs = g4.G4RegionStore.GetInstance()
        self.g4_region = rs.FindOrCreateRegion(self.name)
        self.g4_region.SetUserLimits(self.g4_user_limits)
        self.g4_region.SetProductionCuts(self.g4_production_cuts)
        for vol in self.root_logical_volumes.values():
            self.g4_region.AddRootLogicalVolume(vol.g4_logical_volume, True)
        for lv in self.volumes.values():
            lv.g4_logical_volume.SetRegion(self.g4_region)

    def initialize_g4_production_cuts(self):
        if self.g4_production_cuts is not None:
            gate.fatal("g4_production_cuts already initialized.")
        self.g4_production_cuts = g4.G4ProductionCuts()
        for pname, cut in self.production_cuts.items():
            if cut is not None:
                self.g4_production_cuts.SetProductionCut(cut, pname)

    def initialize_g4_user_limits(self):
        if self.g4_user_limits is not None:
            gate.fatal("g4_user_limits already initialized.")
        self.g4_user_limits = g4.G4UserLimits()

        if self.tracking_cuts["max_step_size"] is None:
            self.g4_user_limits.SetMaxAllowedStep(gate.FLOAT_MAX)
        else:
            self.g4_user_limits.SetMaxAllowedStep(self.tracking_cuts["max_step_size"])

        if self.tracking_cuts["max_track_length"] is None:
            self.g4_user_limits.SetUserMaxTrackLength(gate.FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTrackLength(
                self.tracking_cuts["max_track_length"]
            )

        if self.tracking_cuts["max_time"] is None:
            self.g4_user_limits.SetUserMaxTime(gate.FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTime(self.tracking_cuts["max_time"])

        if self.tracking_cuts["min_ekine"] is None:
            self.g4_user_limits.SetUserMinEkine(0.0)
        else:
            self.g4_user_limits.SetUserMinEkine(self.tracking_cuts["min_ekine"])

        if self.tracking_cuts["min_range"] is None:
            self.g4_user_limits.SetUserMinRange(0.0)
        else:
            self.g4_user_limits.SetUserMinRange(self.tracking_cuts["min_range"])
