from box import Box
import pathlib
import numpy as np
import json
import re
import icrp107_database

from ..utility import g4_units
from ..exception import fatal

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
    "annihilation",
    "fission",
    "betaD",
    "b-spectra",  # beta spectras, both beta+ and beta-
]

DEFAULT_DATABASE = "icrp107"
DEFAULT_SPECTRUM_TYPE = "gamma"


def get_spectrum(
    rad_name: str, spectrum_type=DEFAULT_SPECTRUM_TYPE, database=DEFAULT_DATABASE
) -> Box:
    """
    Retrieve the spectrum of a given radionuclide from the specified database.

    Parameters
    ----------
    rad_name : str
        The name of the radionuclide in Gate format (e.g. "Tc99m", "Lu177").

    spectrum_type : str, optional
        The type of spectrum to retrieve. Default is "gamma". Must be one of
        "gamma", "beta+", "beta-", or "e+". icrp107 allows also one of
        "alpha", "X", "neutron", "auger", "IE", "alpha recoil", "annihilation", "fission", "betaD", "b-spectra".
        In the case of beta spectras, make use of the
        :py:func:`set_source_energy_spectrum` function instead.

    database : str, optional
        The database to retrieve the spectrum from. Default is "icrp107".
        If not "icrp107", we use radar data for gammas and beta-, and LNHB data for beta+.

    Returns
    -------
    Box
        A Box object containing the spectrum data.

    Raises
    ------
    fatal
        If the specified database does not contain the requested spectrum type.
    """
    if database == "icrp107":
        return __get_icrp107_spectrum(rad_name, spectrum_type)
    else:
        if spectrum_type == "beta+" or spectrum_type == "e+":
            return __read_beta_plus_spectra(rad_name)
        elif spectrum_type == "beta-" or spectrum_type == "e-":
            return __get_rad_beta_spectrum(rad_name)
        elif spectrum_type == "gamma":
            return __get_rad_gamma_spectrum(rad_name)
        else:  # FIXME use icrp107 for missing spectrum types
            fatal(f"databse {database} doesn't contain spectrum type {spectrum_type}")


def set_source_energy_spectrum(source, rad: str, database=DEFAULT_DATABASE) -> None:
    """
    Set the energy spectrum of a source.

    Parameters
    ----------
    source : a source
        The source to set the energy spectrum for
    rad : str
        The name of the radionuclide to use
    database : str, optional
        The database to use. The default is "icrp107".

    Notes
    -----
    The source particle must be set before calling this function.
    If the source particle is "beta-/e-" or "beta+/e+", the function will use the
    "b-spectra" spectrum from the database data.
    Otherwise, the function will use the discrete spectrum for the given particle.

    """
    if (
        source.particle == "beta-"
        or source.particle == "e-"
        or source.particle == "beta+"
        or source.particle == "e+"
    ):
        rad_spectrum = get_spectrum(rad, "b-spectra", database)
        source.energy.type = "spectrum_histogram"
        source.energy.spectrum_weights = rad_spectrum.weights[:-1]
        source.energy.spectrum_energy_bin_edges = rad_spectrum.energies
    else:
        rad_spectrum = get_spectrum(rad, source.particle, database)
        source.energy.type = "spectrum_discrete"
        source.energy.spectrum_weights = rad_spectrum.weights
        source.energy.spectrum_energies = rad_spectrum.energies


def __gate_radname_to_icrp107(rad_name: str) -> str:
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


icrp107_time_units = {
    "ms": g4_units.millisecond,
    "s": g4_units.second,
    "m": g4_units.minute,
    "h": g4_units.hour,
    "d": g4_units.day,
    "y": g4_units.year,
}


def __convert_icrp107_time_unit(icrp_time_unit: str) -> float:
    """
    Convert an ICRP 107 time unit to its corresponding value in GATE units.

    Parameters
    ----------
    icrp_time_unit : str
        The time unit from ICRP 107. Valid options are "ms" (milliseconds),
        "s" (seconds), "m" (minutes), "h" (hours), "d" (days), and "y" (years).

    Returns
    -------
    float
        The equivalent time value in GATE units.

    Raises
    ------
    Exception
        If the provided time unit is not recognized.
    """
    if icrp_time_unit in icrp107_time_units:
        return icrp107_time_units[icrp_time_unit]
    else:
        fatal(f"unit {icrp_time_unit} not recognized")


def __read_beta_plus_spectra(rad_name):
    """
    read the file downloaded from LNHB
    there are 15 lines-long header to skip
    first column is E(keV)
    second column is dNtot/dE b+
    WARNING : bins width is not uniform (need to scale for density)
    """
    if rad_name not in all_beta_plus_radionuclides:
        # FIXME use icrp107 for missing isotopes
        fatal(f"rad_name {rad_name} not in {all_beta_plus_radionuclides}")

    filename = (
        f"{gate_source_path}/beta_plus_spectra/{rad_name}/beta+_{rad_name}_tot.bs"
    )
    data = np.genfromtxt(filename, usecols=(0, 1), skip_header=15, dtype=float)
    # FIXME convert to MeV before return
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
    data = __read_beta_plus_spectra(rad_name)
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


def __get_icrp107_spectrum(rad_name: str, spectrum_type=DEFAULT_SPECTRUM_TYPE) -> Box:
    """
    Get the spectrum of a given radionuclide according to ICRP107 recommendations.

    Parameters
    ----------
    rad_name : str
        The name of the radionuclide in Gate format, e.g. "Tc99m", "Lu177"

    spectrum_type : str
        The type of spectrum to retrieve. Must be one of "gamma", "beta-", "beta+", "alpha", "X", "neutron", "auger", "IE", "alpha recoil", "annihilation", "fission", "betaD", "b-spectra"

    Returns
    -------
    Box
        A Box with two keys: "energies" and "weights". The first contains the energy of each emission, the second contains the weight of each emission (summing to 1).

    Raises
    ------
    fatal
        If the radionuclide or spectrum type is not valid.
    """
    rad = __gate_radname_to_icrp107(rad_name)
    icrp107_data = icrp107_database.get_icrp107_spectrum(rad, spectrum_type)

    # convert to Box with unit
    gate_data = {}
    gate_data["energies"] = np.array(
        [v * g4_units.MeV for v in icrp107_data["energies"]]
    )
    gate_data["weights"] = np.array([v for v in icrp107_data["weights"]])
    gate_data["half_life"] = icrp107_data["half_life"] * __convert_icrp107_time_unit(
        icrp107_data["time_unit"]
    )
    return Box(gate_data)


def __get_rad_gamma_spectrum(rad):
    path = gate_source_path.parent / "data" / "rad_gamma_spectrum.json"
    with open(path, "r") as f:
        data = json.load(f)

    # consider lower case
    data = {key.lower(): value for key, value in data.items()}
    rad = rad.lower()

    if rad not in data:
        # FIXME use icrp107 for missing isotopes
        fatal(f"get_rad_gamma_spectrum: {path} does not contain data for ion {rad}")

    # select data for specific ion
    data = Box(data[rad])

    data.energies = np.array(data.energies) * g4_units.MeV
    data.weights = np.array(data.weights)

    return data


def __get_rad_beta_spectrum(rad: str):
    path = gate_source_path.parent / "data" / "rad_beta_spectrum.json"
    with open(path, "r") as f:
        data = json.load(f)

    if rad not in data:
        # FIXME use icrp107 for missing isotopes
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
