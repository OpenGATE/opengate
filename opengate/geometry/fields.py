from ..base import GateObject

import opengate_core as g4
from ..utility import g4_units

# ! ======= KNOWN TODO'S ========
# ! - implement the possibility of choosing the stepper type and equation type
# ! - bind the sextupole magnetic field geant4 implementation
# ! - implement mapped fields (e.g., from a CSV file)
# ! -
# ! =============================


class FieldBase(GateObject):
    """Base class for electric and magnetic fields."""

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

        self.g4_field = None

        self.attached_to = []
        self._field_changes_energy = False

    @property
    def field_changes_energy(self) -> bool:
        """Whether the field changes particle energy (False for magnetic, True for others)."""
        return self._field_changes_energy

    def create_field_manager(self) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        msg = "create_field_manager() must be implemented in subclasses."
        raise NotImplementedError(msg)

    def close(self) -> None:
        self.g4_field = None
        self.attached_to = []
        super().close()


class MagneticField(FieldBase):
    """Base class for magnetic fields."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Magnetic fields don't change particle energy
        self._field_changes_energy = False

        self.g4_equation_of_motion = None
        self.g4_integrator_stepper = None
        self.g4_integration_driver = None
        self.g4_chord_finder = None

    def _create_field(self) -> None:
        """Create the G4 field object. Override."""
        msg = "_create_field() must be implemented in subclasses."
        raise NotImplementedError(msg)

    def create_field_manager(self) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        # Create the G4 field object (subclass responsibility)
        self._create_field()

        # Create equation of motion, stepper, driver, chord finder TODO: allow user choice
        self.g4_equation_of_motion = g4.G4Mag_UsualEqRhs(self.g4_field)
        self.g4_integrator_stepper = g4.G4ClassicalRK4(
            self.g4_equation_of_motion,
            6,      # number of variables for magnetic field = 6 (x,y,z + px,py,pz)
        )
        self.g4_integration_driver = g4.G4MagInt_Driver(
            self.step_minimum,
            self.g4_integrator_stepper,
            6,      # number of variables for magnetic field = 6 (x,y,z + px,py,pz)
            0,      # no verbosity
        )
        self.g4_chord_finder = g4.G4ChordFinder(self.g4_integration_driver)
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
        self.g4_integration_driver = None
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
                "doc": "Field vector [Bx, By, Bz]. Each component in magnetic field strength units (e.g., Tesla).",
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


class QuadrupoleMagneticField(MagneticField):
    """Quadrupole magnetic field with gradient."""

    # hints for IDE
    gradient: float

    user_info_defaults = {
        "gradient": (
            0,
            {
                "doc": "Field gradient in magnetic field strength units per unit length (e.g., Tesla/meter).",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_field(self) -> None:
        """Create the quadrupole magnetic field."""
        self.g4_field = g4.G4QuadrupoleMagField(self.gradient)


class CustomMagneticField(MagneticField):
    """Custom magnetic field defined by a Python callback function."""

    # hints for IDE
    field_function: callable

    user_info_defaults = {
        "field_function": (
            None,
            {
                "doc": "Python function that takes [x, y, z, t] and returns [Bx, By, Bz].",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_field(self) -> None:
        """Create the custom magnetic field using the Python trampoline."""
        if self.field_function is None:
            raise ValueError(
                "field_function must be provided for CustomMagneticField"
            )

        # Check if the function returns 3 components
        test_point = [0, 0, 0, 0]
        result = self.field_function(test_point)
        if len(result) != 3:
            raise ValueError(
                "field_function must return a list of 3 components: [Bx, By, Bz]"
            )

        # Create a custom G4MagneticField subclass that calls our Python function
        class _PyMagneticField(g4.G4MagneticField):
            def __init__(inner_self, callback):
                super().__init__()
                inner_self._callback = callback

            def GetFieldValue(inner_self, point):
                return inner_self._callback(point)

        self.g4_field = _PyMagneticField(self.field_function)


class ElectroMagneticField(FieldBase):
    """Base class for electromagnetic fields."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Electromagnetic fields change particle energy
        self._field_changes_energy = True

        self.g4_equation_of_motion = None
        self.g4_integrator_stepper = None
        self.g4_integration_driver = None
        self.g4_chord_finder = None

    def _create_field(self) -> None:
        """Create the G4 field object. Override in subclasses."""
        msg = "_create_field() must be implemented in subclasses."
        raise NotImplementedError(msg)

    def create_field_manager(self) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        # Create the field (subclass responsibility)
        self._create_field()

        self.g4_equation_of_motion = g4.G4EqMagElectricField(self.g4_field)
        self.g4_integrator_stepper = g4.G4ClassicalRK4(
            self.g4_equation_of_motion,
            8,      # number of variables for electromagnetic field = 8 (x,y,z + px,py,pz + t + E)
        )

        self.g4_integration_driver = g4.G4MagInt_Driver(
            self.step_minimum,
            self.g4_integrator_stepper,
            8,      # number of variables for electromagnetic field = 8 (x,y,z + px,py,pz + t + E)
            0
        )

        self.g4_chord_finder = g4.G4ChordFinder(self.g4_integration_driver)
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
        self.g4_integration_driver = None
        self.g4_integrator_stepper = None
        self.g4_equation_of_motion = None
        super().close()


class ElectricField(ElectroMagneticField):
    """Base class for pure electric fields."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Electric fields change particle energy
        self._field_changes_energy = True


class UniformElectricField(ElectricField):
    """Uniform electric field with constant field vector."""

    # hints for IDE
    field_vector: list

    user_info_defaults = {
        "field_vector": (
            [0, 0, 0],
            {
                "doc": "Field vector [Ex, Ey, Ez] in Geant4 units.",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_field(self) -> None:
        """Create the uniform electric field."""
        self.g4_field = g4.G4UniformElectricField(g4.G4ThreeVector(*self.field_vector))


class CustomElectricField(ElectricField):
    """Custom electric field defined by a Python callback function."""

    # hints for IDE
    field_function: callable

    user_info_defaults = {
        "field_function": (
            None,
            {
                "doc": "Python function that takes [x, y, z, t] and returns [Ex, Ey, Ez].",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_field(self) -> None:
        """Create the custom electric field using the Python trampoline."""
        if self.field_function is None:
            raise ValueError(
                "field_function must be provided for CustomElectricField"
            )

        # Check if the function returns 3 components
        test_point = [0, 0, 0, 0]
        result = self.field_function(test_point)
        if len(result) != 3:
            raise ValueError(
                "field_function must return a list of 3 components: [Ex, Ey, Ez]"
            )

        # Create a custom G4ElectricField subclass that calls our Python function
        class _PyElectricField(g4.G4ElectricField):
            def __init__(inner_self, callback):
                super().__init__()
                inner_self._callback = callback

            def GetFieldValue(inner_self, point):
                return inner_self._callback(point)

        self.g4_field = _PyElectricField(self.field_function)


class UniformElectroMagneticField(ElectroMagneticField):
    """Uniform electromagnetic field with constant magnetic and electric field vectors."""

    # hints for IDE
    magnetic_field_vector: list
    electric_field_vector: list

    user_info_defaults = {
        "magnetic_field_vector": (
            [0, 0, 0],
            {
                "doc": "Magnetic field vector [Bx, By, Bz] in Geant4 units.",
            },
        ),
        "electric_field_vector": (
            [0, 0, 0],
            {
                "doc": "Electric field vector [Ex, Ey, Ez] in Geant4 units.",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_field(self) -> None:
        """Create the uniform electromagnetic field using the Python trampoline."""
        bx, by, bz = self.magnetic_field_vector
        ex, ey, ez = self.electric_field_vector

        # Create a custom G4ElectroMagneticField subclass with constant field values
        class _PyUniformEMField(g4.G4ElectroMagneticField):
            def __init__(inner_self, b_field, e_field):
                super().__init__()
                inner_self._b_field = b_field
                inner_self._e_field = e_field

            def GetFieldValue(inner_self, point):
                # Return constant [Bx, By, Bz, Ex, Ey, Ez]
                return [
                    inner_self._b_field[0],
                    inner_self._b_field[1],
                    inner_self._b_field[2],
                    inner_self._e_field[0],
                    inner_self._e_field[1],
                    inner_self._e_field[2],
                ]

            def DoesFieldChangeEnergy(inner_self):
                return True

        self.g4_field = _PyUniformEMField([bx, by, bz], [ex, ey, ez])


class CustomElectroMagneticField(ElectroMagneticField):
    """Custom electromagnetic field defined by a Python callback function."""

    # hints for IDE
    field_function: callable

    user_info_defaults = {
        "field_function": (
            None,
            {
                "doc": "Python function that takes [x, y, z, t] and returns [Bx, By, Bz, Ex, Ey, Ez].",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_field(self) -> None:
        """Create the custom electromagnetic field using the Python trampoline."""
        if self.field_function is None:
            raise ValueError(
                "field_function must be provided for CustomElectroMagneticField"
            )

        # Check if the function returns 6 components
        test_point = [0, 0, 0, 0]
        result = self.field_function(test_point)
        if len(result) != 6:
            raise ValueError(
                "field_function must return a list of 6 components: [Bx, By, Bz, Ex, Ey, Ez]"
            )

        # Create a custom G4ElectroMagneticField subclass that calls our Python function
        class _PyElectroMagneticField(g4.G4ElectroMagneticField):
            def __init__(inner_self, callback):
                super().__init__()
                inner_self._callback = callback

            def GetFieldValue(inner_self, point):
                return inner_self._callback(point)

            def DoesFieldChangeEnergy(inner_self):
                return True

        self.g4_field = _PyElectroMagneticField(self.field_function)

