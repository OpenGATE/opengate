from box import Box
import os
import pathlib
import numpy as np
import json
import re

from ..actors.base import _setter_hook_attached_to
from ..base import GateObject, process_cls
from ..utility import g4_units
from ..exception import fatal
from ..definitions import __world_name__

gate_source_path = pathlib.Path(__file__).parent.resolve()

# http://www.lnhb.fr/nuclear-data/module-lara/
all_beta_plus_radionuclides = [
    "F18",
    "Ga68",
    "Zr89",
    "Na22",
    "C11",
    "N13",
    "O15",
    "Rb82",
]

icrp107_emissions = [
    "alpha",
    "beta-",
    "beta+",
    "gamma",
    "X",
    "neutron",
    "auger",
    "IE",
    "alpha recoil",
    "anihilation",
    "fission",
    "betaD",
    "b-spectra",
]


def gate_radname_to_icrp107(rad_name: str) -> str:
    """
    Convert a radionuclide name from GATE to ICRP 107 format.

    GATE format is for example "F18" and ICRP 107 format is "F-18"

    Parameters
    ----------
    rad_name : str
        radionuclide name in GATE format

    Returns
    -------
    str
        radionuclide name in ICRP 107 format
    """
    excited = rad_name[-1] == "m"  # Handle Tc-99m
    at_num = re.findall(r"\d+", rad_name)[0]  # Extract atomic number
    name = rad_name[:-1] if excited else rad_name  # Remove final m
    elem = name.replace(at_num, "").replace("-", "")  # Find element code
    elem = elem[0].upper() + elem[1:]  # Fix
    return f'{elem}-{at_num}{"m" if excited else ""}'


def convert_icrp107_time_unit(icrp_time_unit: str) -> float:
    if icrp_time_unit == "ms":
        return g4_units.millisecond
    elif icrp_time_unit == "s":
        return g4_units.second
    elif icrp_time_unit == "m":
        return g4_units.minute
    elif icrp_time_unit == "h":
        return g4_units.hour
    elif icrp_time_unit == "d":
        return g4_units.day
    elif icrp_time_unit == "y":
        return g4_units.year
    else:
        fatal(f"unit {icrp_time_unit} not recognized")


def read_beta_plus_spectra(rad_name):
    """
    read the file downloaded from LNHB
    there are 15 lines-long header to skip
    first column is E(keV)
    second column is dNtot/dE b+
    WARNING : bins width is not uniform (need to scale for density)
    """
    filename = (
        f"{gate_source_path}/beta_plus_spectra/{rad_name}/beta+_{rad_name}_tot.bs"
    )
    data = np.genfromtxt(filename, usecols=(0, 1), skip_header=15, dtype=float)
    return data


def compute_bins_density(bins):
    """
    Given a list of (energy) bins center, compute the width of each bin.
    """
    lower = np.roll(bins, 1)
    lower[0] = 0
    upper = bins
    dx = upper - lower
    return dx


def get_rad_yield(rad_name):
    if rad_name not in all_beta_plus_radionuclides:
        return 1.0
    data = read_beta_plus_spectra(rad_name)
    ene = data[:, 0] / 1000  # convert from KeV to MeV
    proba = data[:, 1]
    _, total = compute_cdf_and_total_yield(proba, ene)
    total = total * 1000  # (because was in MeV)
    return total


def compute_cdf_and_total_yield(data, bins):
    """
    Compute the CDF (Cumulative Density Function) of a list of non-uniform energy bins
    with associated probability.
    Also return the total probability.
    """
    dx = compute_bins_density(bins)
    p = data * dx
    total = p.sum()
    cdf = np.cumsum(p) / total
    return cdf, total


def get_icrp107_spectrum(rad_name: str, spectrum_type="gamma") -> Box:
    """
    Get the spectrum of a given radionuclide according to ICRP107 recommendations.

    Parameters
    ----------
    rad_name : str
        The name of the radionuclide in Gate format, e.g. "Tc99m", "Lu177"

    spectrum_type : str
        The type of spectrum to retrieve. Must be one of "gamma", "beta-", "beta+", "alpha", "X", "neutron", "auger", "IE", "alpha recoil", "anihilation", "fission", "betaD", "b-spectra"

    Returns
    -------
    Box
        A Box with two keys: "energies" and "weights". The first contains the energy of each emission, the second contains the weight of each emission (summing to 1).

    Raises
    ------
    fatal
        If the radionuclide or spectrum type is not valid.
    """
    rad = gate_radname_to_icrp107(rad_name)
    path = pathlib.Path(os.path.dirname(__file__)).parent
    path = path / "data" / "icrp107" / f"{rad}.json"

    if not path.exists():
        fatal(f"get_icrp107_spectrum: {rad} is not contained in the icrp 107 database")

    if spectrum_type not in icrp107_emissions:  # Convert particle name to spectrum type
        spectrum_type = (
            spectrum_type.lower().replace("e-", "beta-").replace("e+", "beta+")
        )

    if spectrum_type not in icrp107_emissions:
        fatal(f"get_icrp107_spectrum: {spectrum_type} is not valid")

    with open(path, "rb") as f:
        data = json.loads(json.load(f))

        # convert to Box
        gate_data = {}
        gate_data["energies"] = np.array(
            [v[0] * g4_units.MeV for v in data["emissions"][spectrum_type]]
        )
        gate_data["weights"] = np.array(
            [v[1] for v in data["emissions"][spectrum_type]]
        )
        gate_data["half_life"] = data["half_life"] * convert_icrp107_time_unit(
            data["time_unit"]
        )
        return Box(gate_data)


def get_rad_gamma_spectrum(rad):
    path = (
        pathlib.Path(os.path.dirname(__file__))
        / ".."
        / "data"
        / "rad_gamma_spectrum.json"
    )
    with open(path, "r") as f:
        data = json.load(f)

    # consider lower case
    data = {key.lower(): value for key, value in data.items()}
    rad = rad.lower()

    if rad not in data:
        fatal(f"get_rad_gamma_spectrum: {path} does not contain data for ion {rad}")

    # select data for specific ion
    data = Box(data[rad])

    data.energies = np.array(data.energies) * g4_units.MeV
    data.weights = np.array(data.weights)

    return data


def get_rad_beta_spectrum(rad: str):
    path = (
        pathlib.Path(os.path.dirname(__file__))
        / ".."
        / "data"
        / "rad_beta_spectrum.json"
    )
    with open(path, "r") as f:
        data = json.load(f)

    if rad not in data:
        fatal(f"get_rad_beta_spectrum: {path} does not contain data for ion {rad}")

    # select data for specific ion
    data = Box(data[rad])

    bin_edges = data.energy_bin_edges
    n = len(bin_edges) - 1
    energies = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(n)]

    data.energy_bin_edges = np.array(data.energy_bin_edges) * g4_units.MeV
    data.weights = np.array(data.weights)
    data.energies = np.array(energies)

    return data


def set_source_rad_energy_spectrum(source, rad):
    rad_spectrum = get_rad_gamma_spectrum(rad)

    source.particle = "gamma"
    source.energy.type = "spectrum_discrete"
    source.energy.spectrum_weights = rad_spectrum.weights
    source.energy.spectrum_energies = rad_spectrum.energies


def set_source_icrp107_energy_spectrum(source, rad: str) -> None:
    """
    Set the energy spectrum of a source according to the ICRP107 recommendations.

    Parameters
    ----------
    source : a source
        The source to set the energy spectrum for
    rad : str
        The name of the radionuclide to use

    Notes
    -----
    The source particle must be set before calling this function.
    If the source particle is "beta-/e-" or "beta+/e+", the function will use the
    "b-spectra" spectrum from the ICRP107 data.
    Otherwise, the function will use the discrete spectrum for the given particle.

    """
    if (
        source.particle == "beta-"
        or source.particle == "e-"
        or source.particle == "beta+"
        or source.particle == "e+"
    ):
        rad_spectrum = get_icrp107_spectrum(rad, "b-spectra")
        source.energy.type = "spectrum_histogram"
        source.energy.spectrum_weights = rad_spectrum.weights[:-1]
        source.energy.spectrum_energy_bin_edges = rad_spectrum.energies
    else:
        rad_spectrum = get_icrp107_spectrum(rad, source.particle)
        source.energy.type = "spectrum_discrete"
        source.energy.spectrum_weights = rad_spectrum.weights
        source.energy.spectrum_energies = rad_spectrum.energies


class SourceBase(GateObject):
    """
    Base class for all source types.
    """

    user_info_defaults = {
        "attached_to": (
            __world_name__,
            {
                "doc": "Name of the volume to which the source is attached.",
                "setter_hook": _setter_hook_attached_to,
            },
        ),
        "mother": (
            None,
            {
                "deprecated": "The user input parameter 'mother' is deprecated. Use 'attached_to' instead. ",
            },
        ),
        "start_time": (
            None,
            {
                "doc": "Starting time of the source",
            },
        ),
        "end_time": (
            None,
            {
                "doc": "End time of the source",
            },
        ),
        "n": (
            0,
            {
                "doc": "Number of particle to generate (exclusive with 'activity')",
            },
        ),
        "activity": (
            0,
            {
                "doc": "Activity of the source in Bq (exclusive with 'n')",
            },
        ),
        "half_life": (
            -1,
            {
                "doc": "Half-life decay (-1 if no decay). Only when used with 'activity'",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        GateObject.__init__(self, *args, **kwargs)
        # all times intervals
        self.run_timing_intervals = None

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def __setstate__(self, state):
        super().__setstate__(state)
        self.__initcpp__()

    def dump(self):
        sec = g4_units.s
        start = "no start time"
        end = "no end time"
        if self.user_info.start_time is not None:
            start = f"{self.user_info.start_time / sec} sec"
        if self.user_info.end_time is not None:
            end = f"{self.user_info.end_time / sec} sec"
        s = (
            f"Source name        : {self.user_info.physics_list_name}\n"
            f"Source type        : {self.user_info.type}\n"
            f"Start time         : {start}\n"
            f"End time           : {end}"
        )
        return s

    def initialize_source_before_g4_engine(self, source):
        pass

    def initialize_start_end_time(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if not self.start_time:
            self.start_time = run_timing_intervals[0][0]
        if not self.end_time:
            self.end_time = run_timing_intervals[-1][1]

    def initialize(self, run_timing_intervals):
        self.initialize_start_end_time(run_timing_intervals)
        # this will initialize and set user_info to the cpp side
        self.InitializeUserInfo(self.user_info)

    def add_to_source_manager(self, source_manager):
        source_manager.AddSource(self)

    def prepare_output(self):
        pass

    def can_predict_number_of_events(self):
        return True


process_cls(SourceBase)
