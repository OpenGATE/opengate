from box import Box
from scipy.spatial.transform import Rotation
import os
import pathlib
import numpy as np
import json

import opengate_core as g4
from ..actors.base import _setter_hook_attached_to
from ..base import GateObject, process_cls
from ..utility import g4_units
from ..exception import fatal, warning
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
    cdf, total = compute_cdf_and_total_yield(proba, ene)
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


def get_rad_gamma_spectrum(rad):
    path = (
        pathlib.Path(os.path.dirname(__file__))
        / ".."
        / "data"
        / "rad_gamma_spectrum.json"
    )
    with open(path, "r") as f:
        data = json.load(f)

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


def get_source_skipped_events(sim, source_name):
    n = sim.get_source_user_info(source_name).fTotalSkippedEvents
    # FIXME this is *not* the correct way to do. Workaround until source is refactored
    n = n * sim.number_of_threads
    return n


def get_source_zero_events(sim, source_name):
    n = sim.get_source_user_info(source_name).fTotalZeroEvents
    # FIXME this is *not* the correct way to do. Workaround until source is refactored
    n = n * sim.number_of_threads
    return n


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

    def __str__(self):
        s = f"{self.user_info.name}: {self.user_info}"
        return s

    def __getstate__(self):
        print("SourceBase get state")
        state_dict = super().__getstate__()
        return state_dict

    def __setstate__(self, state):
        print("SourceBase __setstate__")
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

    def create_g4_source_TO_REMOVE(self):
        fatal('The function "create_g4_source" *must* be overridden')

    def initialize_source_before_g4_engine(self, source):
        pass

    def initialize_start_end_time(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if not self.user_info.start_time:
            self.user_info.start_time = run_timing_intervals[0][0]
        if not self.user_info.end_time:
            self.user_info.end_time = run_timing_intervals[-1][1]

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


def _generic_source_default_position():
    return Box(
        {
            "type": "point",
            "radius": 0,
            "sigma_x": 0,
            "sigma_y": 0,
            "size": [0, 0, 0],
            "translation": [0, 0, 0],
            "rotation": Rotation.identity().as_matrix(),
            "confine": None,
        }
    )


def _generic_source_default_direction():
    return Box(
        {
            "type": "iso",
            "theta": [0, 180],
            "phi": [0, 360],
            "momentum": [0, 0, 1],
            "focus_point": [0, 0, 0],
            "sigma": [0, 0],
            "acceptance_angle": _generic_source_default_aa(),
            "accolinearity_flag": False,
            "histogram_theta_weight": [],
            "histogram_theta_angle": [],
            "histogram_phi_weight": [],
            "histogram_phi_angle": [],
        }
    )


def _generic_source_default_aa():
    deg = g4_units.deg
    return Box(
        {
            "skip_policy": "SkipEvents",
            "volumes": [],
            "intersection_flag": False,
            "normal_flag": False,
            "normal_vector": [0, 0, 1],
            "normal_tolerance": 3 * deg,
        }
    )


def _generic_source_default_energy():
    return Box(
        {
            "type": "mono",
            "mono": 0,
            "sigma_gauss": 0,
            "is_cdf": False,
            "min_energy": None,
            "max_energy": None,
            "spectrum_type": None,
        }
    )


def _setter_hook_generic_source_particle(self, particle):
    # particle must be a str
    if not isinstance(particle, str):
        fatal(f"the .particle user info must be a str, while it is {type(str)}")
    # if it does not start with ion, we consider this is a simple particle (gamma, e+ etc)
    if not particle.startswith("ion"):
        return particle
    # if start with ion, it is like 'ion 9 18' with Z A E
    words = particle.split(" ")
    if len(words) > 1:
        self.ion.Z = int(words[1])
    if len(words) > 2:
        self.ion.A = int(words[2])
    if len(words) > 3:
        self.ion.E = int(words[3])
    return particle


class GenericSource(SourceBase, g4.GateGenericSource):
    """
    GenericSource close to the G4 SPS, but a bit simpler.
    The G4 source created by this class is GateGenericSource.
    """

    # hints for IDE
    particle: str
    ion: Box
    weight: float
    weight_sigma: float
    user_particle_life_time: float
    tac_times: list
    tac_activities: list
    direction_relative_to_attached_volume: bool
    position: Box
    direction: Box
    energy: Box

    user_info_defaults = {
        "particle": (
            "gamma",
            {
                "doc": "Name of the particle generated by the source (gamma, e+ ... or an ion such as 'ion 9 18')",
                "setter_hook": _setter_hook_generic_source_particle,
            },
        ),
        "ion": (
            Box({"Z": 0, "A": 0, "E": 0}),
            {
                "doc": "If the particle is an ion, you must set Z: Atomic Number, A: Atomic Mass (nn + np +nlambda), E: Excitation energy (i.e. for metastable)"
            },
        ),
        "weight": (
            -1,
            {"doc": "Particle initial weight (for variance reduction technique)"},
        ),
        "weight_sigma": (
            -1,
            {
                "doc": "if not negative, the weights of the particle are a Gaussian distribution with this sigma"
            },
        ),
        "user_particle_life_time": (
            -1,
            {"doc": "FIXME "},
        ),
        "tac_times": (
            None,
            {
                "doc": "TAC: Time Activity Curve, this set the vector for the times. Must be used with tac_activities."
            },
        ),
        "tac_activities": (
            None,
            {
                "doc": "TAC: Time Activity Curve, this set the vector for the activities. Must be used with tac_times."
            },
        ),
        "direction_relative_to_attached_volume": (
            False,
            {
                "doc": "When the volume is move (with dynamic parametrisation) should we update the direction of the particle or not?"
            },
        ),
        "position": (
            _generic_source_default_position(),
            {"doc": "Define the position of the primary particles"},
        ),
        "direction": (
            _generic_source_default_direction(),
            {"doc": "Define the direction of the primary particles"},
        ),
        "energy": (
            _generic_source_default_energy(),
            {"doc": "Define the energy of the primary particles"},
        ),
    }

    def __init__(self, *args, **kwargs):
        print(f"GenericSource __init__")
        self.__initcpp__()  # FIXME should be first ????
        super().__init__(self, *args, **kwargs)
        print("current user_info", self.user_info)
        if not self.user_info.particle.startswith("ion"):
            return
        words = self.user_info.particle.split(" ")
        if len(words) > 1:
            self.user_info.ion.Z = words[1]
        if len(words) > 2:
            self.user_info.ion.A = words[2]
        if len(words) > 3:
            self.user_info.ion.E = words[3]

        # will be set by g4 source
        self.fTotalZeroEvents = 0
        self.fTotalSkippedEvents = 0

    def __initcpp__(self):
        g4.GateGenericSource.__init__(self)

    def initialize(self, run_timing_intervals):
        print(f"Generic source initialize", run_timing_intervals)

        if not isinstance(self.user_info.position, Box):
            fatal(
                f"Generic Source: user_info.position must be a Box, but is: {self.user_info.position}"
            )
        if not isinstance(self.user_info.direction, Box):
            fatal(
                f"Generic Source: user_info.direction must be a Box, but is: {self.user_info.direction}"
            )
        if not isinstance(self.user_info.energy, Box):
            fatal(
                f"Generic Source: user_info.energy must be a Box, but is: {self.user_info.energy}"
            )

        if self.user_info.particle == "back_to_back":
            # force the energy to 511 keV
            self.user_info.energy.type = "mono"
            self.user_info.energy.mono = 511 * g4_units.keV

        # check energy type
        l = [
            "mono",
            "gauss",
            "F18_analytic",
            "O15_analytic",
            "C11_analytic",
            "histogram",
            "spectrum_discrete",
            "spectrum_histogram",
            "range",
        ]
        l.extend(all_beta_plus_radionuclides)
        if not self.user_info.energy.type in l:
            fatal(
                f"Cannot find the energy type {self.user_info.energy.type} for the source {self.user_info.name}.\n"
                f"Available types are {l}"
            )

        # check energy spectrum type if not None
        valid_spectrum_types = [
            "discrete",
            "histogram",
            "interpolated",
        ]
        if self.user_info.energy.spectrum_type is not None:
            if self.user_info.energy.spectrum_type not in valid_spectrum_types:
                fatal(
                    f"Cannot find the energy spectrum type {self.user_info.energy.spectrum_type} for the source {self.user_info.name}.\n"
                    f"Available types are {valid_spectrum_types}"
                )

        # special case for beta plus energy spectra
        # FIXME put this elsewhere
        if self.user_info.particle == "e+":
            if self.user_info.energy.type in all_beta_plus_radionuclides:
                data = read_beta_plus_spectra(self.user_info.energy.type)
                ene = data[:, 0] / 1000  # convert from KeV to MeV
                proba = data[:, 1]
                cdf, total = compute_cdf_and_total_yield(proba, ene)
                # total = total * 1000  # (because was in MeV)
                # self.user_info.activity *= total
                self.user_info.energy.is_cdf = True
                self.SetEnergyCDF(ene)
                self.SetProbabilityCDF(cdf)

        self.update_tac_activity()

        # histogram parameters: histogram_weight, histogram_energy"
        ene = self.user_info.energy
        if ene.type == "histogram":
            if len(ene.histogram_weight) != len(ene.histogram_energy):
                fatal(
                    f"For the source {self.user_info.name} energy, "
                    f'"histogram_energy" and "histogram_weight" must have the same length'
                )

        # check direction type
        l = ["iso", "histogram", "momentum", "focused", "beam2d"]
        if not self.user_info.direction.type in l:
            fatal(
                f"Cannot find the direction type {self.user_info.direction.type} for the source {self.user_info.name}.\n"
                f"Available types are {l}"
            )

        # logic for half life and user_particle_life_time
        ui = self.user_info
        if ui.half_life > 0:
            # if the user set the half life and not the user_particle_life_time
            # we force the latter to zero
            if ui.user_particle_life_time < 0:
                ui.user_particle_life_time = 0

        # initialize
        SourceBase.initialize(self, run_timing_intervals)

        if self.user_info.n > 0 and self.user_info.activity > 0:
            fatal(f"Cannot use both n and activity, choose one: {self.user_info}")
        if self.user_info.n == 0 and self.user_info.activity == 0:
            fatal(f"Choose either n or activity : {self.user_info}")
        if self.user_info.activity > 0:
            self.user_info.n = 0
        if self.user_info.n > 0:
            self.user_info.activity = 0
        # warning for non-used ?
        # check confine
        if self.user_info.position.confine:
            if self.user_info.position.type == "point":
                warning(
                    f"In source {self.user_info.name}, "
                    f"confine is used, while position.type is point ... really ?"
                )

    def check_ui_activity(self, ui):
        if ui.n > 0 and ui.activity > 0:
            fatal(f"Cannot use both n and activity, choose one: {self.user_info}")
        if ui.n == 0 and ui.activity == 0:
            fatal(f"Choose either n or activity : {self.user_info}")
        if ui.activity > 0:
            ui.n = 0
        if ui.n > 0:
            ui.activity = 0

    def check_confine(self, ui):
        if ui.position.confine:
            if ui.position.type == "point":
                warning(
                    f"In source {ui.name}, "
                    f"confine is used, while position.type is point ... really ?"
                )

    def prepare_output(self):
        print("prepare_output")
        SourceBase.prepare_output(self)
        # store the output from G4 object
        # FIXME will be refactored like the actors
        # self.user_info.fTotalZeroEvents = self.g4_source.fTotalZeroEvents
        # self.user_info.fTotalSkippedEvents = self.g4_source.fTotalSkippedEvents
        # self.user_info.fTotalZeroEvents = self.fTotalZeroEvents
        # self.user_info.fTotalSkippedEvents = self.fTotalSkippedEvents

    def update_tac_activity(self):
        ui = self.user_info
        if ui.tac_times is None and ui.tac_activities is None:
            return
        n = len(ui.tac_times)
        if n != len(ui.tac_activities):
            fatal(
                f"option tac_activities must have the same size as tac_times in source '{ui.name}'"
            )
        # it is important to set the starting time for this source as the tac
        # may start later than the simulation timing
        ui.start_time = ui.tac_times[0]
        ui.activity = ui.tac_activities[0]
        self.g4_source.SetTAC(ui.tac_times, ui.tac_activities)

    def can_predict_number_of_events(self):
        aa = self.user_info.direction.acceptance_angle
        if aa.intersection_flag or aa.normal_flag:
            if aa.skip_policy == "ZeroEnergy":
                return True
            return False
        return True


'''
class TemplateSource(SourceBase):
    """
    Source template: to create a new type of source, copy-paste
    this file and adapt to your needs.
    Also declare the source type in the file helpers_source.py
    """

    type_name = "TemplateSource"

    @staticmethod
    def set_default_user_info(user_info):
        SourceBase.set_default_user_info(user_info)
        # initial user info
        user_info.float_value = None
        user_info.vector_value = None

    def create_g4_source(self):
        return opengate_core.GateTemplateSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def initialize(self, run_timing_intervals):
        # Check user_info type
        if self.user_info.float_value is None:
            fatal(
                f"Error for source {self.user_info.name}, float_value must be a float"
            )
        if self.user_info.vector_value is None:
            fatal(
                f"Error for source {self.user_info.name}, vector_value must be a vector"
            )

        # initialize
        SourceBase.initialize(self, run_timing_intervals)
'''


process_cls(SourceBase)
process_cls(GenericSource)
