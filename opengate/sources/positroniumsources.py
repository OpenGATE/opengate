from box import Box
from scipy.spatial.transform import Rotation

import opengate_core as g4
from .base import SourceBase
from .utility import (
    all_beta_plus_radionuclides,
    get_spectrum,
    compute_cdf_and_total_yield,
)
from ..actors.biasingactors import generic_source_default_aa
from ..base import process_cls
from ..utility import g4_units
from ..exception import fatal, warning


def _positronium_source_default_position():
    return Box({
        "type": "point",
        "radius": 0,
        "sigma_x": 0,
        "sigma_y": 0,
        "size": [0, 0, 0],
        "translation": [0, 0, 0],
        "rotation": Rotation.identity().as_matrix(),
        "confine": None,
    })


class PositroniumSource(SourceBase, g4.GatePositroniumSource):
    """
    positroniumSource close to the G4 SPS, but a bit simpler.
    The G4 source created by this class is GatePositroniumSource.
    """

    user_info_defaults = {
        # "position": (
        #     _positronium_source_default_position(),
        #     {
        #         "doc": "Define the position of the primary particles"
        #     },
        # ),
        "positronium_fractions": ([], {
            "doc":
            "Fractions for positronium decay channels"
        }),
        "positronium_lifetimes": ([], {
            "doc": "Lifetimes of each decay channel "
        }),
        "decay_kinds": ([], {
            "doc": "Kind of each decay chanel"
        }),
        "prompt_photon_probabilities": ([], {
            "doc":
            "Prompt photon probability of each decay channel"
        }),
        "prompt_photon_energies": ([], {
            "doc": "Photon energy of each decay channel"
        })
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__initcpp__()
        self.total_zero_events = 0
        self.total_skipped_events = 0

    def __initcpp__(self):
        g4.GatePositroniumSource.__init__(self)

    def initialize(self, run_timing_intervals):
        SourceBase.initialize(self, run_timing_intervals)

        parameters = [
            self.positronium_fractions, self.positronium_lifetimes,
            self.decay_kinds, self.prompt_photon_probabilities,
            self.prompt_photon_energies
        ]

        if any(len(p) == 0 for p in parameters):
            fatal("Positronium must have at least one decay channel")

        if not all(len(parameters[0]) == len(p) for p in parameters[1:]):
            fatal("Positronium source parameters have different lengths")

    def prepare_output(self):
        SourceBase.prepare_output(self)
        # store the output from G4 object
        # self.total_zero_events = self.GetTotalZeroEvents()
        # self.total_skipped_events = self.GetTotalSkippedEvents()


process_cls(PositroniumSource)
