import opengate_core as g4
from .generic import GenericSource
from ..base import process_cls
from ..exception import fatal


class PositroniumSource(GenericSource, g4.GatePositroniumSource):
    """
    positroniumSource close to the G4 SPS, but a bit simpler.
    The G4 source created by this class is GatePositroniumSource.
    """

    user_info_defaults = {
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
        }),
        "mean_positron_range": ([], {
            "doc":
            "Mean positron range of each decay channel"
        }),
        "electron_capture_probabilities": ([], {
            "doc":
            "Electron capture probability of each decay channel"
        })
    }

    def __init__(self, *args, **kwargs):
        self.__initcpp__()
        super().__init__(self, *args, **kwargs)

    def __initcpp__(self):
        g4.GatePositroniumSource.__init__(self)

    def initialize(self, run_timing_intervals):

        parameters = [
            self.positronium_fractions, self.positronium_lifetimes,
            self.decay_kinds, self.prompt_photon_probabilities,
            self.prompt_photon_energies, self.mean_positron_range,
            self.electron_capture_probabilities
        ]

        if any(len(p) == 0 for p in parameters):
            fatal("Positronium must have at least one decay channel")

        if not all(len(parameters[0]) == len(p) for p in parameters[1:]):
            fatal("Positronium source parameters have different lengths")

        if self.particle != "gamma":
            fatal("Positronium source can only emit gamma particles")

        GenericSource.initialize(self, run_timing_intervals)


process_cls(PositroniumSource)
