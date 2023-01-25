import numpy as np

import opengate as gate
import opengate_core as g4
from box import Box
from scipy.spatial.transform import Rotation


class GenericSource(gate.SourceBase):
    """
    GeneriSource close to the G4 SPS, but a bit simpler.
    """

    type_name = "Generic"

    @staticmethod
    def set_default_user_info(user_info):
        gate.SourceBase.set_default_user_info(user_info)
        # initial user info
        user_info.particle = "gamma"
        user_info.ion = Box()
        user_info.n = 0
        user_info.activity = 0
        user_info.weight = -1
        user_info.weight_sigma = -1
        user_info.half_life = -1  # negative value is no half_life
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
        user_info.direction = Box()
        user_info.direction.type = "iso"
        user_info.direction.momentum = [0, 0, 1]
        user_info.direction.focus_point = [0, 0, 0]
        user_info.direction.sigma = [0, 0]
        user_info.direction.acceptance_angle = Box()
        user_info.direction.acceptance_angle.skip_policy = "SkipEvents"  # or ZeroEnergy
        user_info.direction.acceptance_angle.volumes = []
        user_info.direction.acceptance_angle.intersection_flag = False
        user_info.direction.acceptance_angle.normal_flag = False
        user_info.direction.acceptance_angle.normal_vector = [0, 0, 1]
        deg = gate.g4_units("deg")
        user_info.direction.acceptance_angle.normal_tolerance = 3 * deg
        # energy
        user_info.energy = Box()
        user_info.energy.type = "mono"
        user_info.energy.mono = 0
        user_info.energy.sigma_gauss = 0
        user_info.energy.is_cdf = False
        user_info.energy.min_energy = None
        user_info.energy.max_energy = None

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GateGenericSource()

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
        #    gate.fatal(f'Generic Source: user_info must be a Box, but is: {self.user_info}')
        if not isinstance(self.user_info, gate.UserInfo):
            gate.fatal(
                f"Generic Source: user_info must be a UserInfo, but is: {self.user_info}"
            )
        if not isinstance(self.user_info.position, Box):
            gate.fatal(
                f"Generic Source: user_info.position must be a Box, but is: {self.user_info.position}"
            )
        if not isinstance(self.user_info.direction, Box):
            gate.fatal(
                f"Generic Source: user_info.direction must be a Box, but is: {self.user_info.direction}"
            )
        if not isinstance(self.user_info.energy, Box):
            gate.fatal(
                f"Generic Source: user_info.energy must be a Box, but is: {self.user_info.energy}"
            )

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
        l.extend(gate.all_beta_plus_radionuclides)
        if not self.user_info.energy.type in l:
            gate.fatal(
                f"Cannot find the energy type {self.user_info.energy.type} for the source {self.user_info.name}.\n"
                f"Available types are {l}"
            )

        # special case for beta plus energy spectra
        if self.user_info.particle == "e+":
            if self.user_info.energy.type in gate.all_beta_plus_radionuclides:
                data = gate.read_beta_plus_spectra(self.user_info.energy.type)
                ene = data[:, 0] / 1000  # convert from KeV to MeV
                proba = data[:, 1]
                cdf, total = gate.compute_cdf_and_total_yield(proba, ene)
                # total = total * 1000  # (because was in MeV)
                # self.user_info.activity *= total
                self.user_info.energy.is_cdf = True
                self.g4_source.SetEnergyCDF(ene)
                self.g4_source.SetProbabilityCDF(cdf)

        # initialize
        gate.SourceBase.initialize(self, run_timing_intervals)

        if self.user_info.n > 0 and self.user_info.activity > 0:
            gate.fatal(f"Cannot use both n and activity, choose one: {self.user_info}")
        if self.user_info.n == 0 and self.user_info.activity == 0:
            gate.fatal(f"Choose either n or activity : {self.user_info}")
        if self.user_info.activity > 0:
            self.user_info.n = 0
        if self.user_info.n > 0:
            self.user_info.activity = 0
        # warning for non-used ?
        # check confine
        if self.user_info.position.confine:
            if self.user_info.position.type == "point":
                gate.warning(
                    f"In source {self.user_info.name}, "
                    f"confine is used, while position.type is point ... really ?"
                )

    def prepare_output(self):
        gate.SourceBase.prepare_output(self)
        # store the output from G4 object
        self.fTotalZeroEvents = self.g4_source.fTotalZeroEvents
        self.fTotalSkippedEvents = self.g4_source.fTotalSkippedEvents


def get_source_skipped_events(output, source_name):
    ui = output.simulation.user_info
    n = 0
    if ui.number_of_threads > 1 or ui.force_multithread_mode:
        for i in range(1, ui.number_of_threads + 1):
            s = output.get_source_MT(source_name, i)
            n += s.fTotalSkippedEvents
    else:
        n = output.get_source(source_name).fTotalSkippedEvents
    return n


def get_source_zero_events(output, source_name):
    ui = output.simulation.user_info
    n = 0
    if ui.number_of_threads > 1 or ui.force_multithread_mode:
        for i in range(1, ui.number_of_threads + 1):
            s = output.get_source_MT(source_name, i)
            n += s.fTotalZeroEvents
    else:
        n = output.get_source(source_name).fTotalZeroEvents
    return n
