from box import Box
from scipy.spatial.transform import Rotation
import pathlib
import numpy as np

import opengate_core
from ..utility import g4_units
from ..exception import fatal, warning
from ..definitions import __world_name__
from ..userelement import UserElement

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


def get_rad_gamma_energy_spectrum(rad):
    weights = {}
    energies = {}
    MeV = g4_units.MeV
    # convert to lowcase
    rad = rad.lower()
    # Tc99m
    weights["tc99m"] = [0.885]
    energies["tc99m"] = [0.140511 * MeV]
    # Lu177
    weights["lu177"] = [0.001726, 0.0620, 0.000470, 0.1038, 0.002012, 0.00216]
    energies["lu177"] = [
        0.0716418 * MeV,
        0.1129498 * MeV,
        0.1367245 * MeV,
        0.2083662 * MeV,
        0.2496742 * MeV,
        0.3213159 * MeV,
    ]

    # In111
    weights["in111"] = [0.000015, 0.9061, 0.9412]
    energies["in111"] = [0.15081 * MeV, 0.17128 * MeV, 0.24535 * MeV]
    # I131
    weights["i131"] = [
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
    energies["i131"] = [
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
    source.particle = "gamma"
    source.energy.type = "spectrum_lines"
    source.energy.spectrum_weight = w
    source.energy.spectrum_energy = en


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


class SourceBase(UserElement):
    """
    Base class for all source types.
    """

    @staticmethod
    def set_default_user_info(user_info):
        UserElement.set_default_user_info(user_info)
        # user properties shared by all sources
        user_info.mother = __world_name__
        user_info.start_time = None
        user_info.end_time = None
        user_info.n = 0
        user_info.activity = 0
        user_info.half_life = -1  # negative value is no half_life

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from SourceBase
        super().__init__(user_info)
        # the cpp counterpart of the source
        self.g4_source = self.create_g4_source()
        # all times intervals
        self.run_timing_intervals = None
        # threading
        self.current_thread_id = None

    def __str__(self):
        s = f"{self.user_info.name}: {self.user_info}"
        return s

    def __getstate__(self):
        if self.verbose_getstate:
            warning(
                f"Getstate SourceBase {self.user_info.type_name} {self.user_info.name}"
            )
        self.simulation = None
        self.g4_source = None
        return self.__dict__

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

    def create_g4_source(self):
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
        self.g4_source.InitializeUserInfo(self.user_info.__dict__)

    def add_to_source_manager(self, source_manager):
        source_manager.AddSource(self.g4_source)

    def prepare_output(self):
        pass

    def can_predict_number_of_events(self):
        return True


class GenericSource(SourceBase):
    """
    GenericSource close to the G4 SPS, but a bit simpler.
    The G4 source created by this class is GateGenericSource.
    """

    type_name = "GenericSource"

    @staticmethod
    def set_default_user_info(user_info):
        SourceBase.set_default_user_info(user_info)

        # initial user info
        user_info.particle = "gamma"
        user_info.ion = Box()
        user_info.weight = -1
        user_info.weight_sigma = -1
        user_info.user_particle_life_time = -1  # negative means : by default
        user_info.tac_times = None
        user_info.tac_activities = None
        user_info.direction_relative_to_attached_volume = False

        # ion
        user_info.ion = Box()
        user_info.ion.Z = 0  # Z: Atomic Number
        user_info.ion.A = 0  # A: Atomic Mass (nn + np +nlambda)
        user_info.ion.E = 0  # E: Excitation energy (i.e. for metastable)

        # position
        user_info.position = Box()
        user_info.position.type = "point"
        user_info.position.radius = 0
        user_info.position.sigma_x = 0
        user_info.position.sigma_y = 0
        user_info.position.size = [0, 0, 0]
        user_info.position.translation = [0, 0, 0]
        user_info.position.rotation = Rotation.identity().as_matrix()
        user_info.position.confine = None

        # angle (direction)
        deg = g4_units.deg
        user_info.direction = Box()
        user_info.direction.type = "iso"
        user_info.direction.theta = [0, 180 * deg]
        user_info.direction.phi = [0, 360 * deg]
        user_info.direction.momentum = [0, 0, 1]
        user_info.direction.focus_point = [0, 0, 0]
        user_info.direction.sigma = [0, 0]
        user_info.direction.acceptance_angle = Box()
        user_info.direction.acceptance_angle.skip_policy = "SkipEvents"  # or ZeroEnergy
        user_info.direction.acceptance_angle.volumes = []
        user_info.direction.acceptance_angle.intersection_flag = False
        user_info.direction.acceptance_angle.normal_flag = False
        user_info.direction.acceptance_angle.normal_vector = [0, 0, 1]
        user_info.direction.acceptance_angle.normal_tolerance = 3 * deg
        user_info.direction.accolinearity_flag = False  # only for back_to_back source
        user_info.direction.histogram_theta_weight = []
        user_info.direction.histogram_theta_angle = []
        user_info.direction.histogram_phi_weight = []
        user_info.direction.histogram_phi_angle = []

        # energy
        user_info.energy = Box()
        user_info.energy.type = "mono"
        user_info.energy.mono = 0
        user_info.energy.sigma_gauss = 0
        user_info.energy.is_cdf = False
        user_info.energy.min_energy = None
        user_info.energy.max_energy = None
        user_info.energy.histogram_weight = None
        user_info.energy.histogram_energy = None

    def create_g4_source(self):
        return opengate_core.GateGenericSource()

    def __init__(self, user_info):
        super().__init__(user_info)
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

    def initialize(self, run_timing_intervals):
        # Check user_info type
        # if not isinstance(self.user_info, Box):
        #    fatal(f'Generic Source: user_info must be a Box, but is: {self.user_info}')
        # Infer whether self.user_info is a UserInfo object
        # without explicitly using the UserInfo class (circular import)
        if not hasattr(self.user_info, "element_type"):
            fatal(
                f"Generic Source: user_info must be a UserInfo, but is: {self.user_info}"
            )
        # if not isinstance(self.user_info, UserInfo):
        #     fatal(
        #         f"Generic Source: user_info must be a UserInfo, but is: {self.user_info}"
        #     )
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
            "spectrum_lines",
            "range",
        ]
        l.extend(all_beta_plus_radionuclides)
        if not self.user_info.energy.type in l:
            fatal(
                f"Cannot find the energy type {self.user_info.energy.type} for the source {self.user_info.name}.\n"
                f"Available types are {l}"
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
                self.g4_source.SetEnergyCDF(ene)
                self.g4_source.SetProbabilityCDF(cdf)

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
        SourceBase.prepare_output(self)
        # store the output from G4 object
        # FIXME will be refactored like the actors
        self.user_info.fTotalZeroEvents = self.g4_source.fTotalZeroEvents
        self.user_info.fTotalSkippedEvents = self.g4_source.fTotalSkippedEvents

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
