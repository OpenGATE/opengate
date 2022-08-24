from .VoxelsSource import *
from .GANSource import *
import pathlib

"""
    List of source types: Generic, Voxels etc

    Energy spectra for beta+ emitters
"""

source_type_names = {GenericSource, VoxelsSource, GANSource}
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

    px = -sintheta * cosphi
    py = -sintheta * sinphi
    pz = -costheta

    # concat
    v = np.column_stack((px, py, pz))
    return v
