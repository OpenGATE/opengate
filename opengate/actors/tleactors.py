import opengate_core as g4
from ..exception import fatal
from ..utility import g4_units
from ..base import process_cls
from .actoroutput import (
    ActorOutputSingleImageOfHistogram,
    ActorOutputImage,
    ActorOutputSingleImage,
    UserInterfaceToActorOutputImage,
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
    plot the time of flight of the neutron against the energy of the PGs emitted in monomode
    """

    user_info_defaults = {
        "timebins": (
            100,
            {
                "doc": "Number of time bins",
            },
        ),
        "energybins": (
            100,
            {
                "doc": "Number of energy bins",
            },
        ),
        "output_name": (
            "output/defaults-TOF.mhd",
            {
                "doc": "output_name",
            },
        ),
    }

    user_output_config = {
        "correl": {
            "actor_output_class": ActorOutputSingleImage,
            "active": True,
        }
    }

    def __init__(self, *args, **kwargs) -> None:
        VoxelDepositActor.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateVoxelizedPromptGammaTLEActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "BeginOfRunAction",
                "EndOfRunAction",
                "BeginOfEventAction",
                "SteppingAction",
                "EndOfRunActionMasterThread",
            }
        )

    def initialize(self):
        self.check_user_input()
        VoxelDepositActor.initialize(self)
        self.user_output.correl.set_active(True)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()
        self.SetPhysicalVolumeName(self.user_info.get("attached_to"))

    def BeginOfRunActionMasterThread(self, run_index):
        g4.GateVoxelizedPromptGammaTLEActor.BeginOfRunActionMasterThread(
            self, run_index
        )

    def EndOfRunActionMasterThread(self, run_index):
        # Save the image
        filename = g4.GateVoxelizedPromptGammaTLEActor.GetOutputImage(self)
        itk_image = itk.imread(filename)
        itk.imwrite(itk_image, self.user_info["output_name"])
        self.user_output.correl.store_data(run_index, itk_image)
        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateVoxelizedPromptGammaTLEActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)

process_cls(TLEDoseActor)
process_cls(VoxelizedPromptGammaTLEActor)
