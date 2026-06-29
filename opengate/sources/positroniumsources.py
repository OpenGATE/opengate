from box import Box
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
        "channels_from_fractions": (Box({
            "fractions": [],
            "decay_kinds": []
        }), {
            "doc":
            "Parameters to define channels from fractions"
        }),
        "channels_from_intensities": (Box({
            "intensities": [],
            "positron_interactions": []
        }), {
            "doc":
            "Parameters to define channels from intensities"
        }),
        "positronium_lifetimes": ([], {
            "doc": "Lifetimes of each decay channel "
        }),
        "prompt_gamma_probabilities": ([], {
            "doc":
            "Prompt photon probability of each decay channel"
        }),
        "prompt_gamma_energies": ([], {
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

        fractions_provided = len(self.channels_from_fractions.fractions) > 0
        intensities_provided = len(
            self.channels_from_intensities.intensities) > 0

        if fractions_provided and intensities_provided:
            fatal("Cannot provide both fractions and intensities")
        elif not fractions_provided and not intensities_provided:
            fatal("Either fractions or intensities must be provided")
        elif fractions_provided:
            specific_parameters = [
                self.channels_from_fractions,
                self.channels_from_fractions.decay_kinds
            ]
        elif intensities_provided:
            specific_parameters = [
                self.channels_from_intensities.positron_interactions,
                self.channels_from_intensities.positron_interactions
            ]
        else:
            fatal("Should never happen")

        common_parameters = [
            self.positronium_lifetimes, self.prompt_gamma_probabilities,
            self.prompt_gamma_energies, self.mean_positron_range,
            self.electron_capture_probabilities
        ]

        parameters = [*specific_parameters, *common_parameters]

        # if not all(
        #         len(common_parameters[0]) == len(p) for p in parameters[1:]):
        #     fatal("Positronium source parameters have different lengths")

        # if any(len(p) == 0 for p in common_parameters):
        #     fatal("Positronium must have at least one decay channel")

        if intensities_provided:
            self.calculate_channels_from_lifetimes()

        if self.particle != "gamma":
            fatal("Positronium source can only emit gamma particles")

        GenericSource.initialize(self, run_timing_intervals)

    # Helpers

    para_ps_lifetime_ns = .1244
    para_to_ortho_ps_fraction = 1.0 / 3.0
    ortho_ps_mean_lifetime_ns = 142.
    hyperfine_coefficient = 372

    def calculate_channels_from_lifetimes(self):

        if len(self.channels_from_intensities.positron_interactions) == 0:
            fatal(
                "Could not calculate fractions from lifetimes. fPositronInteractions is empty."
            )

        fractions = []
        decay_kinds = []
        positronium_lifetimes = []
        prompt_gamma_probabilities = []
        prompt_gamma_energies = []
        positron_interactions = []
        electron_capture_probabilities = []
        mean_positron_range = []

        pPs_index = -1

        for i, _ in enumerate(
                self.channels_from_intensities.positron_interactions):
            if self.channels_from_intensities.positron_interactions[
                    i] == "kParaPs":
                if pPs_index == -1:
                    pPs_index = i
                else:
                    fatal(
                        "Positron interaction list can only contain one parapositronium"
                    )
            else:
                intens2G, intens3G = PositroniumSource.calc_fractions_from_lifetime(
                    self.channels_from_intensities.intensities[i],
                    self.positronium_lifetimes[i],
                    self.channels_from_intensities.positron_interactions[i])

                fractions.append(intens2G)
                fractions.append(intens3G)
                decay_kinds.append("k2Gamma")
                decay_kinds.append("k3Gamma")

                positronium_lifetimes.append(self.positronium_lifetimes[i])
                positronium_lifetimes.append(self.positronium_lifetimes[i])
                prompt_gamma_probabilities.append(
                    self.prompt_gamma_probabilities[i])
                prompt_gamma_probabilities.append(
                    self.prompt_gamma_probabilities[i])
                prompt_gamma_energies.append(self.prompt_gamma_energies[i])
                prompt_gamma_energies.append(self.prompt_gamma_energies[i])
                positron_interactions.append(
                    self.channels_from_intensities.positron_interactions[i])
                positron_interactions.append(
                    self.channels_from_intensities.positron_interactions[i])

                # TODO deal with default values for electron capture probabilities and mean positron range in all cases
                if len(self.electron_capture_probabilities) > 0:
                    electron_capture_probabilities.append(
                        self.electron_capture_probabilities[i])
                    electron_capture_probabilities.append(
                        self.electron_capture_probabilities[i])
                else:
                    electron_capture_probabilities.append(0.)
                    electron_capture_probabilities.append(0.)
                if len(self.mean_positron_range) > 0:
                    mean_positron_range.append(self.mean_positron_range[i])
                    mean_positron_range.append(self.mean_positron_range[i])
                else:
                    mean_positron_range.append(0.)
                    mean_positron_range.append(0.)

        pPs_inter = PositroniumSource.calc_pps_fraction_from_ops(
            fractions, positron_interactions)
        if pPs_inter > 0:
            if pPs_index < 0:
                fatal(
                    "A non-zero para-Ps fraction was derived from the ortho-Ps components, but no kParaPs entry was provided in fPositronInteractions to supply its lifetime/prompt-gamma parameters."
                )
            fractions.append(pPs_inter)
            positronium_lifetimes.append(self.positronium_lifetimes[pPs_index])
            prompt_gamma_probabilities.append(
                self.prompt_gamma_probabilities[pPs_index])
            prompt_gamma_energies.append(self.prompt_gamma_energies[pPs_index])
            decay_kinds.append("k2Gamma")
            positron_interactions.append("kParaPs")
            if len(self.electron_capture_probabilities) > 0:
                electron_capture_probabilities.append(
                    self.electron_capture_probabilities[pPs_index])
            else:
                electron_capture_probabilities.append(0.)
            if len(self.mean_positron_range) > 0:
                mean_positron_range.append(self.mean_positron_range[pPs_index])
            else:
                mean_positron_range.append(0.)

        fractions = PositroniumSource.normalize_fractions(fractions)

        self.channels_from_fractions.fractions = fractions
        self.channels_from_fractions.decay_kinds = decay_kinds
        self.positronium_lifetimes = positronium_lifetimes
        self.prompt_gamma_probabilities = prompt_gamma_probabilities
        self.prompt_gamma_energies = prompt_gamma_energies
        self.channels_from_intensities.positron_interactions = positron_interactions
        self.electron_capture_probabilities = electron_capture_probabilities
        self.mean_positron_range = mean_positron_range

    @staticmethod
    def calc_pps_fraction_from_ops(fractions, inters):
        sum_ops = sum(fractions[i] for i, inter in enumerate(inters)
                      if inter == "kOrthoPs")
        return sum_ops * PositroniumSource.para_to_ortho_ps_fraction

    @staticmethod
    def calc_fractions_from_lifetime(intensity, lifetime, inter):
        if inter == "kDirect":
            intens2G = intensity * (
                PositroniumSource.hyperfine_coefficient -
                1.) / PositroniumSource.hyperfine_coefficient
            intens3G = intensity / PositroniumSource.hyperfine_coefficient
            return intens2G, intens3G

        if inter == "kOrthoPs":
            intens2G = intensity * (
                PositroniumSource.ortho_ps_mean_lifetime_ns -
                lifetime) / PositroniumSource.ortho_ps_mean_lifetime_ns
            intens3G = intensity * lifetime / PositroniumSource.ortho_ps_mean_lifetime_ns
            return intens2G, intens3G

        fatal("This function does not handle parapositrionium case.")

    @staticmethod
    def calc_fraction_from_ops_lifetime(intensity, lifetime, decay):
        nominator = 0.
        if intensity > 0. and lifetime > 0.:
            if decay == g4.PositroniumDecayKind.k2Gamma:
                nominator = PositroniumSource.ortho_ps_mean_lifetime_ns - lifetime
            elif decay == g4.PositroniumDecayKind.k3Gamma:
                nominator = lifetime
            else:
                raise ValueError
            return intensity * nominator / PositroniumSource.ortho_ps_mean_lifetime_ns
        return nominator

    @staticmethod
    def normalize_fractions(fractions):
        fractions_sum = sum(fractions)
        return [f / fractions_sum for f in fractions]


process_cls(PositroniumSource)
