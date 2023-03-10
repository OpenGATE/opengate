from .VoxelsSource import *
from .GANPairsSource import *
from .PencilBeamSource import *
import pathlib
import radioactivedecay as rd

"""
    List of source types: Generic, Voxels etc

    Energy spectra for beta+ emitters
"""

source_type_names = {
    GenericSource,
    VoxelsSource,
    GANSource,
    GANPairsSource,
    PencilBeamSource,
}
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


def define_ion_gamma_sources(source_type, name):
    print("define sources ", name)

    # create base user_info from a "fake" GS or VS (or GANS ?)
    ui = gate.UserInfo("Source", source_type, name)

    # some default param
    ui.energy.type = "ion_gamma"

    # add new parameters with default : ion, options etc
    return ui


def get_nuclide_progeny(nuclide):
    # recurse until stable
    if nuclide.half_life() == "stable":
        return []
    # start a list of daughters
    p = []
    daugthers = nuclide.progeny()
    for d in daugthers:
        p.append(d)
        nuc_d = rd.Nuclide(d)
        p = p + get_nuclide_progeny(nuc_d)
    # remove duplicate
    p = list(set(p))
    return p


def get_ion_gamma_channels(ion, options={}):
    a = ion.a
    z = ion.z
    print(a, z)

    # FIXME
    w = [0.3, 0.3, 0.4]
    ene = [0.200, 0.300, 0.400]

    """ principle
    - (get all daughters A,Z with rd)
    - for each ion :
        - read db file f"z{z}.a{a}"
        - read all gamma lines + half life
        - for each gamma channels
            - read E, intensity, alpha -> compute ?

    For all gamma channels
        - compute relative intensity
        - if daughter order is zero  ground state : final transition E
        - of continue deep in the tree, substracting transition_energy (?)

    Need of BR ???

    """

    # read file as a box, with gamma lines as box
    level_gamma = read_level_gamma(a, z)

    # parse the levels to get all energies
    weights = []
    energies = []
    for level in level_gamma:
        add_weights_and_energy_level(level_gamma, level, weights, energies)

    return w, ene


def add_weights_and_energy_level(level_gamma, level, weights, energies):
    g = level_gamma[level]
    total_intensity = 0
    total_br = 0
    for d in g.daugthers.values():
        total_intensity += d.intensity
        d.br = (1 + d.alpha) * d.intensity
        total_br += d.br
    # print(f'total', total_intensity)
    """
    6) Total internal conversion coefficient : alpha = Ic/Ig
   Note1: total transition is the sum of gamma de-excitation and internal
          conversion. Therefore total branching ratio is proportional to
          (1+alpha)*Ig
   Note2: total branching ratios from a given level do not always sum up to
          100%. They are re-normalized internally.
   Note3: relative probabilities for gamma de-excitation and internal conversion
          are 1/(1+alpha) and alpha/(1+alpha) respectively
    """
    for d in g.daugthers.values():
        if total_br != 0:
            d.br = d.br / total_br
            print(
                f"{level} {d.daughter_order} br ={d.br}   (ig ={d.intensity} alpha={d.alpha})"
            )


def read_level_gamma(a, z, ignore_zero_deex=True):
    # get folder
    data_paths = g4.get_G4_data_path()
    folder = pathlib.Path(data_paths["G4LEVELGAMMADATA"])
    print("data folder", folder)
    ion_filename = folder / f"z{z}.a{a}"
    print(ion_filename)
    with open(ion_filename) as file:
        lines = [line for line in file]
    levels = Box()
    i = 0
    print(len(lines))
    keV = gate.g4_units("keV")
    while i < len(lines) - 1:
        l = Box()
        words = lines[i].split()
        # 1)An integer defining the order index of the level starting by 0  for the ground state
        l.order_level = words[0]
        # 2)A string  defining floating level  (-,+X,+Y,+Z,+U,+V,+W,+R,+S,+T,+A,+B,+C)
        l.floating_level = words[1]
        # 3) Excitation energy of the level (keV)
        l.excitation_energy = float(words[2]) * keV
        # 4) Level half-life (s). A -1 half-life means a stable ground state.
        l.half_life = words[3]
        # 5) JPi information of the level.
        # 6) n_gammas= Number of possible gammas deexcitation channel from the level.
        l.n_gammas = int(words[5])
        # if no channel, we (may) ignore
        if ignore_zero_deex and l.n_gammas == 0:
            i += 1
            continue
        l.daugthers = Box()
        i += 1
        print(i, l)
        for j in range(0, l.n_gammas):
            a = read_one_gamma_deex_channel(lines[i])
            l.daugthers[a.daughter_order] = a
            print("   ", a)
            i += 1
        levels[l.order_level] = l
    print()
    return levels


def read_one_gamma_deex_channel(line):
    keV = gate.g4_units("keV")
    words = line.split()
    l = Box()
    # 1) The order number of the daughter level.
    l.daughter_order = words[0]
    # 2) The energy of the gamma transition.
    l.transition_energy = float(words[1]) * keV
    # 3) The relative gamma emission intensity.
    l.intensity = float(words[2])
    # 4)The multipolarity number with 1,2,3,4,5,6,7 representing E0,E1,M1,E2,M2,E3,M3  monopole transition
    #   and  100*Nx+Ny representing multipolarity transition with Ny and Ny taking the value 1,2,3,4,5,6,7
    #   referring to   E0,E1,M1,E2,M2,E3,M3,.. For example a M1+E2 transition would be written 304.
    #   A value of 0 means an unknown multipolarity.
    # 5)The multipolarity mixing ratio. O means that either the transition is a E1,M1,E2,M2 transition
    #    or the multipolarity mixing ratio is not given in ENSDF.
    # 6) Total internal conversion coefficient : alpha = Ic/Ig
    l.alpha = float(words[5])
    return l


def add_ion_gamma_sources(sim, user_info, bins=200):
    """
    Consider an input 'fake' ion source with a given activity.
    Create a source of gamma for all decay daughters of this ion.

    The gamma spectrum is given according to the XXXX FIXME

    The activity intensity of all sources will be computed with Bateman
    equations during source initialisation, we only set the parameters here.

    """
    print("add all sources")

    # consider the user ion
    words = user_info.particle.split(" ")
    if not user_info.particle.startswith("ion") or len(words) != 3:
        gate.fatal(
            f"The 'ion' option of user_info must be 'ion Z A', while it is {user_info.ion}"
        )
    z = int(words[1])
    a = int(words[2])
    print("ion ", z, a)

    # get list of decay ions
    id = int(f"{z:3}{a:3}0000")
    first_nuclide = rd.Nuclide(id)
    print(first_nuclide)
    # print("half life", nuclide.half_life())
    daughters = get_nuclide_progeny(first_nuclide)
    daughters.append(first_nuclide.nuclide)
    print("all daughters (no order)", daughters)

    # loop to add all sources, we copy all options and update the info
    sources = []
    for daughter in daughters:
        s = sim.add_source(user_info.type_name, f"{user_info.name}_{daughter}")
        s.copy_from(user_info)
        # additional info, specific to ion gamma source
        nuclide = rd.Nuclide(daughter)
        s.particle = "gamma"
        # set gamma lines
        s.energy.type = "spectrum_lines"
        s.energy.ion_gamma_mother = Box({"a": a, "z": z})
        s.energy.ion_gamma_daughter = Box({"a": nuclide.A, "z": nuclide.Z})
        w, ene = gate.get_ion_gamma_channels(s.energy.ion_gamma_daughter)
        s.energy.spectrum_weight = w
        s.energy.spectrum_energy = ene
        # prepare times and activities that will be set during initialisation
        s.tac_from_decay_parameters = {
            "ion_name": first_nuclide,
            "daughter": daughter,
            "bins": bins,
        }
        sources.append(s)

    return sources


def get_tac_from_decay(
    ion_name, daugther_name, start_activity, start_time, end_time, bins
):
    """
    The following will be modified according to the TAC:
    ui.start_time, ui.end_time, ui.activity

    param is ui.tac_from_decay_parameters
    param is a dict with:
    - nuclide: a Nuclide object from radioactivedecay module, with the main ion
    - daughter: the daughter for which we compute the intensity in the time intervals
    - bins: number of bins for the discretised TAC

    - run_timing_intervals: is the list of time range from the Simulation
    """
    ion = rd.Inventory({ion_name: 1.0}, "Bq")
    sec = gate.g4_units("s")
    Bq = gate.g4_units("Bq")
    times = np.linspace(start_time, end_time, num=bins, endpoint=True)
    activities = []
    max_a = 0
    min_a = start_activity
    start_time = -1
    for t in times:
        x = ion.decay(t / sec, "s")
        intensity = x.activities()[daugther_name]
        a = intensity * start_activity
        activities.append(a)
        if start_time == -1 and a > 0:
            start_time = t
        if a > max_a:
            max_a = a
        if a < min_a:
            min_a = a
        # print(f"t {t/sec} {daugther_name} {intensity} {a/Bq}")
    print(
        f"{daugther_name} time range {start_time / sec}  {end_time / sec} "
        f": {start_time/sec} {min_a/Bq} {max_a/Bq}"
    )
    return times, activities
