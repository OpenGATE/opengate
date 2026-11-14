"""GATE 9 fastY90 water kernel with native GATE 10 emission sampling."""

import math

import itk
import numpy as np
import opengate_core as g4

from .generic import GenericSource, _direction_parameters, energy_parameters
from .voxelsources import VoxelSource
from ..base import process_cls
from ..exception import fatal
from ..image import get_info_from_image, update_image_py_to_cpp
from ..utility import ensure_filename_is_str, g4_units


class FastY90Source(VoxelSource):
    """Sample bremsstrahlung photons and positrons from Y-90 decays in water.

    Activity and TAC values specify decays per second. Fixed
    ``number_of_primaries`` specifies transported emissions. Set ``image`` for
    a voxelized decay distribution, or use the usual ``position`` parameters.
    The kernel sets the particle type, energy and direction.
    """

    user_info_defaults = {
        "min_brem_energy": (
            0.0,
            {
                "doc": "Bremsstrahlung cutoff in [0, 2 MeV), rounded down to "
                "a 10 keV boundary as in GATE 9. Does not affect positrons."
            },
        ),
        "positron_probability": (
            3.186e-5,
            {"doc": "Positron yield per Y-90 decay, in [0, 1]."},
        ),
    }

    def create_g4_source(self):
        return g4.GateFastY90Source()

    def resolve_and_validate_config(self, run_timing_intervals, context=None):
        if (
            not math.isfinite(self.min_brem_energy)
            or not 0 <= self.min_brem_energy < 2 * g4_units.MeV
        ):
            fatal(
                f"FastY90Source '{self.name}': min_brem_energy must be finite "
                "and in [0, 2 MeV)."
            )
        if (
            not math.isfinite(self.positron_probability)
            or not 0 <= self.positron_probability <= 1
        ):
            fatal(
                f"FastY90Source '{self.name}': positron_probability must be "
                "finite and in [0, 1]."
            )
        if self.particle != "gamma" or self.energy != energy_parameters():
            fatal(
                f"FastY90Source '{self.name}' sets its own particles and "
                "energies. Leave particle and energy at their defaults."
            )
        if self.direction != _direction_parameters() or len(self.polarization) != 0:
            fatal(
                f"FastY90Source '{self.name}' sets its own isotropic kernel "
                "directions. Leave direction and polarization at their defaults."
            )
        if self.image is not None and self.position.confine is not None:
            fatal(
                f"FastY90Source '{self.name}': confine cannot be combined "
                "with an activity image."
            )
        super().resolve_and_validate_config(run_timing_intervals, context=context)

    def set_transform_from_user_info(self, g4_source):
        info = get_info_from_image(self._current_itk_image)
        distribution = g4_source.GetSPSVoxelPosDistribution()
        update_image_py_to_cpp(
            self._current_itk_image, distribution.cpp_edep_image, False
        )
        distribution.cpp_edep_image.set_spacing(info.spacing)
        distribution.cpp_edep_image.set_direction(np.eye(3))
        # Keep the grid centered in source coordinates. The native source
        # applies position.rotation, position.translation and attached_to once.
        distribution.cpp_edep_image.set_origin(
            -info.size * info.spacing / 2 + info.spacing / 2
        )

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        if self.image is not None:
            if self._current_itk_image is None:
                self._current_itk_image = itk.imread(ensure_filename_is_str(self.image))
            self.set_transform_from_user_info(g4_source)
            self.cumulative_distribution_functions(g4_source)
        GenericSource.initialize_g4_source(self, g4_source, run_timing_intervals)

    def cumulative_distribution_functions(self, g4_source):
        # This also validates replacement images used by dynamic sources.
        if self._cdf_x is None:
            data = itk.array_from_image(self._current_itk_image)
            total = data.sum(dtype=float)
            if (
                data.ndim != 3
                or not np.isfinite(data).all()
                or np.any(data < 0)
                or not np.isfinite(total)
                or total <= 0
            ):
                fatal(
                    f"FastY90Source '{self.name}': image must contain finite, "
                    "nonnegative 3D activity weights with a positive sum."
                )
        super().cumulative_distribution_functions(g4_source)


process_cls(FastY90Source)
