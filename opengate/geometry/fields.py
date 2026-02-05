from ..base import GateObject

from abc import ABC, abstractmethod

import opengate_core as g4
from ..utility import g4_units



class FieldBase(GateObject, ABC):
    """Base class for electric and magnetic fields."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.g4_field = None

        self.attached_to = []
        self._field_changes_energy = False

    @property
    def field_changes_energy(self) -> bool:
        """Whether the field changes particle energy (False for magnetic, True for others)."""
        return self._field_changes_energy

    @abstractmethod
    def create_field_manager(self) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        pass

    def close(self) -> None:
        self.g4_field = None
        self.attached_to = []
        super().close()


class MagneticField(FieldBase):
    """Base class for magnetic fields."""

    # hints for IDE
    step_minimum: float
    delta_chord: float
    delta_one_step: float
    delta_intersection: float
    min_epsilon_step: float
    max_epsilon_step: float

    user_info_defaults = {
        "step_minimum": (
            1e-2 * g4_units.mm,
            {
                "doc": "Minimum step size for the chord finder.",
            },
        ),
        "delta_chord": (
            1e-3 * g4_units.mm,
            {
                "doc": "Maximum miss distance between chord and curved trajectory.",
            },
        ),
        "delta_one_step": (
            1e-3 * g4_units.mm,
            {
                "doc": "Positional accuracy per integration step.",
            },
        ),
        "delta_intersection": (
            1e-4 * g4_units.mm,
            {
                "doc": "Positional accuracy at volume boundaries.",
            },
        ),
        "min_epsilon_step": (
            1e-7,
            {
                "doc": "Minimum relative integration accuracy.",
            },
        ),
        "max_epsilon_step": (
            1e-5,
            {
                "doc": "Maximum relative integration accuracy.",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Magnetic fields don't change particle energy
        self._field_changes_energy = False

        self.g4_equation_of_motion = None
        self.g4_integrator_stepper = None
        self.g4_chord_finder = None

    def _create_field(self) -> None:
        """Create the G4 field object. Override."""
        pass

    def create_field_manager(self) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        # Create the field (implemented by subclasses)
        self._create_field()

        # Create equation of motion, stepper, chord finder
        self.g4_equation_of_motion = g4.G4Mag_UsualEqRhs(self.g4_field)
        self.g4_integrator_stepper = g4.G4ClassicalRK4(self.g4_equation_of_motion, 6)
        self.g4_chord_finder = g4.G4ChordFinder(
            self.g4_field, self.step_minimum, self.g4_integrator_stepper, 0
        )
        self.g4_chord_finder.SetDeltaChord(self.delta_chord)

        # Create and configure field manager
        fm = g4.G4FieldManager(
            self.g4_field, self.g4_chord_finder, self.field_changes_energy
        )
        fm.SetDeltaOneStep(self.delta_one_step)
        fm.SetDeltaIntersection(self.delta_intersection)
        fm.SetMinimumEpsilonStep(self.min_epsilon_step)
        fm.SetMaximumEpsilonStep(self.max_epsilon_step)

        return fm

    def close(self) -> None:
        self.g4_chord_finder = None
        self.g4_integrator_stepper = None
        self.g4_equation_of_motion = None
        super().close()


class UniformMagneticField(MagneticField):
    """Uniform magnetic field with constant field vector."""

    # hints for IDE
    field_vector: list

    user_info_defaults = {
        "field_vector": (
            [0, 0, 0],
            {
                "doc": "Field vector [Bx, By, Bz] in Tesla.",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_field(self) -> None:
        """Create the uniform magnetic field."""
        self.g4_field = g4.G4UniformMagField(
            g4.G4ThreeVector(*self.field_vector)
        )

