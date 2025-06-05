import opengate_core as g4
from ..exception import fatal
from ..utility import g4_units
from ..base import process_cls
from .actoroutput import (
    ActorOutputSingleImageOfHistogram,
)

from ..image import (
    update_image_py_to_cpp,
    get_py_image_from_cpp_image,
    images_have_same_domain,
    resample_itk_image_like,
)
import SimpleITK as sitk
import itk
from .doseactors import DoseActor, VoxelDepositActor


class TLEDoseActor(DoseActor, g4.GateTLEDoseActor):
    """
    TLE = Track Length Estimator

    The Track Length Estimator (TLE) is a variance reduction technique used in Monte Carlo simulations to accelerate dose computation, particularly for photon transport. It calculates the dose contribution by integrating the track length of particles within a voxel, reducing the number of particles required for accurate results. TLE is efficient for photon simulations as it avoids the need to explicitly simulate individual interactions within each voxel.

    The main limitation of TLE is its inability to account for dose delocalization, as it assumes energy deposition occurs along the particle's track within a voxel. TLE is typically restricted to photons with energies below 1-2 MeV for standard voxel sizes, as higher energies may result in larger dose spread beyond the voxel boundaries, reducing accuracy.

    Two databases can be used: EPDL (Evaluated Photon Data Library): Provides detailed photon interaction cross-sections, including photoelectric, Compton scattering, and pair production, for accurate modeling across a wide energy range. NIST (National Institute of Standards and Technology) XCOM database: Supplies photon attenuation and energy absorption coefficients, widely used for material property definitions and dose computations.

    """

    energy_min: float
    energy_max: float
    database: str

    user_info_defaults = {
        "energy_min": (
            0.0,
            {"doc": "Kill the gamma if below this energy"},
        ),
        "energy_max": (
            1.0 * g4_units.MeV,
            {
                "doc": "Above this energy, do not perform TLE (TLE is only relevant for low energy gamma)"
            },
        ),
        "database": (
            "EPDL",
            {
                "doc": "which database to use",
                "allowed_values": ("EPDL", "NIST"),  # "simulated" does not work
            },
        ),
    }

    def __initcpp__(self):
        g4.GateTLEDoseActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "EndOfRunActionMasterThread",
                "BeginOfRunAction",
                "EndOfRunAction",
                "BeginOfEventAction",
                "SteppingAction",
                "PreUserTrackingAction",
            }
        )

    def initialize(self, *args):
        if self.score_in != "material":
            fatal(
                f"TLEDoseActor cannot score in {self.score_in}, only 'material' is allowed."
            )
        super().initialize(args)



class VoxelizedPromptGammaTLEActor(
    VoxelDepositActor, g4.GateVoxelizedPromptGammaTLEActor
):
    """
    FIXME doc todo
    """

    user_info_defaults = {
        "database": (
            None, #stage 0 from Geant4 // upload
            {
                "doc": "TODO",
            },
        ),
        "bins":(
            200,
            {
                "doc": "Number of bins in the histogram",
            },
        ),
        "range":(
            5 * g4_units.ns,
            {
                "doc": "Range of the histogram in ns",
            },
        ),
        "proton":(
            True,
            {
                "doc": "True if the collisions of interest are from the proton, False if it is from the neutron",
            },
        ),
        "energy":(
            True,
            {
                "doc": "True if the quantity of interest is the energy and not the time of flight"
            },
        ),
    }

    user_output_config = {
        "vpg_p_E": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "active": True,
        },
        "vpg_n_E": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "active": False,
        },
        "vpg_p_tof": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "active": False,
        },
        "vpg_n_tof": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "active": False,
        },
    }

    def __init__(self, *args, **kwargs) -> None:
        VoxelDepositActor.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateVoxelizedPromptGammaTLEActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "BeginOfEventAction",
                "SteppingAction",
                "EndOfRunAction",
                "EndOfRunActionMasterThread",
            }
        )

    def initialize(self, *args):
        self.check_user_input()
        VoxelDepositActor.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()
        self.SetPhysicalVolumeName(self.user_info.get("attached_to"))

    def prepare_output_for_run(self, output_name, run_index, **kwargs):
        # need to override because create image is different for img of histo
        self._assert_output_exists(output_name)
        self.user_output[output_name].create_image_of_histograms(
            run_index,
            self.size,
            self.spacing,
            self.bins + 1,
            origin=self.translation,
            **kwargs,
        )

    def BeginOfRunActionMasterThread(self, run_index):
        if self.user_info["proton"] == False :
            if self.user_info["energy"] == False :
                self.prepare_output_for_run("vpg_n_tof", run_index)
                self.push_to_cpp_image("vpg_n_tof", run_index, self.cpp_tof_neutron_image)
            else :
                self.prepare_output_for_run("vpg_n_E", run_index)
                self.push_to_cpp_image("vpg_n_E", run_index, self.cpp_E_neutron_image)
        else :
            if self.user_info["energy"] == False :
                self.prepare_output_for_run("vpg_p_tof", run_index)
                self.push_to_cpp_image("vpg_p_tof", run_index, self.cpp_tof_proton_image)
            else :
                self.prepare_output_for_run("vpg_p_E", run_index)
                self.push_to_cpp_image("vpg_p_E", run_index, self.cpp_E_proton_image)
        g4.GateVoxelizedPromptGammaTLEActor.BeginOfRunActionMasterThread(self, run_index)

    def EndOfRunActionMasterThread(self, run_index):
        print("end of run action master thread")
        if self.user_info["proton"] == False :
            if self.user_info["energy"] == False :
                self.fetch_from_cpp_image("vpg_n_tof", run_index, self.cpp_tof_neutron_image)
                self._update_output_coordinate_system("vpg_n_tof", run_index)
            else:
                self.fetch_from_cpp_image("vpg_n_E", run_index, self.cpp_E_neutron_image)
                self._update_output_coordinate_system("vpg_n_E", run_index)
        if self.user_info["proton"] == True :
            if self.user_info["energy"] == False :
                self.fetch_from_cpp_image("vpg_p_tof", run_index, self.cpp_tof_proton_image)
                self._update_output_coordinate_system("vpg_p_tof", run_index)
            else :
                self.fetch_from_cpp_image("vpg_p_E", run_index, self.cpp_E_proton_image)
                self._update_output_coordinate_system("vpg_p_E", run_index)
        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateVoxelizedPromptGammaTLEActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


process_cls(TLEDoseActor)
process_cls(VoxelizedPromptGammaTLEActor)
