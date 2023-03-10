import opengate as gate
import opengate_core as g4
from box import Box


class CutsAndLimitsRegion(gate.GateObject):
    """FIXME: Documentation of the CutsAndLimitsRegion class."""

    user_info_defaults = {}
    user_info_defaults["tracking_cuts"] = Box()
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

    #   G4double fMaxStep  = 0.;  // max allowed Step size in this volume
    #   G4double fMaxTrack = 0.;  // max total track length
    #   G4double fMaxTime  = 0.;  // max time
    #   G4double fMinEkine = 0.;  // min kinetic energy (only for charged particles)
    #   G4double fMinRange = 0.;  // min remaining range (only for charged particles)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.g4_region = None  # will be created by initialize()
