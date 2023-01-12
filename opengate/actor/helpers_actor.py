import opengate as gate
from .ARFActor import *
from .ARFTrainingDatasetActor import *
from .DoseActor import *
from .DigitizerAdderActor import *
from .DigitizerReadoutActor import *
from .DigitizerEnergyWindowsActor import *
from .DigitizerProjectionActor import *
from .DigitizerBlurringActor import *
from .DigitizerSpatialBlurringActor import *
from .MotionVolumeActor import *
from .PhaseSpaceActor import *
from .SimulationStatisticsActor import *
from .SourceInfoActor import *
from .TestActor import *

actor_type_names = {
    SimulationStatisticsActor,
    DoseActor,
    SourceInfoActor,
    PhaseSpaceActor,
    DigitizerHitsCollectionActor,
    DigitizerAdderActor,
    DigitizerEnergyWindowsActor,
    DigitizerProjectionActor,
    DigitizerReadoutActor,
    DigitizerBlurringActor,
    DigitizerSpatialBlurringActor,
    MotionVolumeActor,
    ARFActor,
    ARFTrainingDatasetActor,
    TestActor,
}
actor_builders = gate.make_builders(actor_type_names)


def get_simplified_digitizer_channels_Tc99m(spect_name, scatter_flag):
    keV = gate.g4_units("keV")
    # Tc99m
    channels = [
        {"name": f"scatter_{spect_name}", "min": 114 * keV, "max": 126 * keV},
        {"name": f"peak140_{spect_name}", "min": 126 * keV, "max": 154 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
    return channels


def get_simplified_digitizer_channels_Lu177(spect_name, scatter_flag):
    # Lu177, Ljungberg2016
    keV = gate.g4_units("keV")
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 96 * keV, "max": 104 * keV},
        {"name": f"peak113_{spect_name}", "min": 104 * keV, "max": 121.48 * keV},
        {"name": f"scatter2_{spect_name}", "min": 122.48 * keV, "max": 133.12 * keV},
        {"name": f"scatter3_{spect_name}", "min": 176.46 * keV, "max": 191.36 * keV},
        {"name": f"peak208_{spect_name}", "min": 192.36 * keV, "max": 223.6 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_In111(spect_name, scatter_flag):
    # In111
    keV = gate.g4_units("keV")
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 150 * keV, "max": 156 * keV},
        {"name": f"peak171_{spect_name}", "min": 156 * keV, "max": 186 * keV},
        {"name": f"scatter2_{spect_name}", "min": 186 * keV, "max": 192 * keV},
        {"name": f"scatter3_{spect_name}", "min": 218 * keV, "max": 224 * keV},
        {"name": f"peak245_{spect_name}", "min": 224 * keV, "max": 272 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_I131(spect_name, scatter_flag):
    # I131
    keV = gate.g4_units("keV")
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 314 * keV, "max": 336 * keV},
        {"name": f"peak364_{spect_name}", "min": 336 * keV, "max": 392 * keV},
        {"name": f"scatter2_{spect_name}", "min": 392 * keV, "max": 414 * keV},
        {"name": f"scatter3_{spect_name}", "min": 414 * keV, "max": 556 * keV},
        {"name": f"scatter4_{spect_name}", "min": 556 * keV, "max": 595 * keV},
        {"name": f"peak637_{spect_name}", "min": 595 * keV, "max": 679 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_rad(spect_name, rad, scatter_flag):
    available_rad = {
        "Tc99m": get_simplified_digitizer_channels_Tc99m,
        "Lu177": get_simplified_digitizer_channels_Lu177,
        "In111": get_simplified_digitizer_channels_In111,
        "I131": get_simplified_digitizer_channels_I131,
    }

    if rad not in available_rad:
        gate.fatal(
            f"Error, the radionuclide {rad} is not known, list of available is: {available_rad}"
        )

    return available_rad[rad](spect_name, scatter_flag)
