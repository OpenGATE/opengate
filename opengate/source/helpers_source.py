from .VoxelsSource import *
from .GANSource import *
from .PencilBeamSource import *
import pathlib

"""
    List of source types: Generic, Voxels etc

    Energy spectra for beta+ emitters
"""

source_type_names = {GenericSource, VoxelsSource, GANSource, PencilBeamSource}
source_builders = gate.make_builders(source_type_names)

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
    if not rad_name in all_beta_plus_radionuclides:
        return 1.0
    data = read_beta_plus_spectra(rad_name)
    ene = data[:, 0] / 1000  # convert from KeV to MeV
    proba = data[:, 1]
    cdf, total = gate.compute_cdf_and_total_yield(proba, ene)
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


def generate_isotropic_directions(
    n, min_theta=0, max_theta=np.pi, min_phi=0, max_phi=2 * np.pi, rs=np.random
):
    """
    like in G4SPSAngDistribution.cc

    Later : do a version with torch (gpu) instead of np (cpu) ?
    """
    u = rs.uniform(0, 1, size=n)
    costheta = np.cos(min_theta) - u * (np.cos(min_theta) - np.cos(max_theta))
    sintheta = np.sqrt(1 - costheta**2)

    v = rs.uniform(0, 1, size=n)
    phi = min_phi + (max_phi - min_phi) * v
    sinphi = np.sin(phi)
    cosphi = np.cos(phi)

    # "direct cosine" method, like in Geant4 (already normalized)
    px = -sintheta * cosphi
    py = -sintheta * sinphi
    pz = -costheta

    # concat
    v = np.column_stack((px, py, pz))

    return v


def get_rad_gamma_energy_spectrum(rad):
    weights = {}
    energies = {}
    MeV = gate.g4_units("MeV")
    # Tc99m
    weights["Tc99m"] = [0.885]
    energies["Tc99m"] = [0.140511 * MeV]
    # Lu177
    weights["Lu177"] = [0.001726, 0.0620, 0.000470, 0.1038, 0.002012, 0.00216]
    energies["Lu177"] = [
        0.0716418 * MeV,
        0.1129498 * MeV,
        0.1367245 * MeV,
        0.2083662 * MeV,
        0.2496742 * MeV,
        0.3213159 * MeV,
    ]

    # In111
    weights["In111"] = [0.000015, 0.9061, 0.9412]
    energies["In111"] = [0.15081 * MeV, 0.17128 * MeV, 0.24535 * MeV]
    # I131
    weights["I131"] = [
        0.02607,
        0.000051,
        0.000211,
        0.00277,
        0.000023,
        0.000581,
        0.0614,
        0.000012,
        0.000046,
        0.000807,
        0.000244,
        0.00274,
        0.00017,
        0.812,
        0.000552,
        0.003540,
        0.0712,
        0.002183,
        0.01786,
    ]
    energies["I131"] = [
        0.080185 * MeV,
        0.0859 * MeV,
        0.163930 * MeV,
        0.177214 * MeV,
        0.23218 * MeV,
        0.272498 * MeV,
        0.284305 * MeV,
        0.2958 * MeV,
        0.3024 * MeV,
        0.318088 * MeV,
        0.324651 * MeV,
        0.325789 * MeV,
        0.3584 * MeV,
        0.364489 * MeV,
        0.404814 * MeV,
        0.503004 * MeV,
        0.636989 * MeV,
        0.642719 * MeV,
        0.722911 * MeV,
    ]

    return weights[rad], energies[rad]


def set_source_rad_energy_spectrum(source, rad):
    w, en = get_rad_gamma_energy_spectrum(rad)
    source.energy.type = "spectrum_lines"
    source.energy.spectrum_weight = w
    source.energy.spectrum_energy = en
