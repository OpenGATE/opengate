from typing import Any

import numpy as np
import opengate_core as g4

from ..base import GateObject, process_cls
from ..geometry.utility import (
    get_transform_world_to_local,
    vec_np_as_g4,
    rot_np_as_g4,
    vec_g4_as_np,
    rot_g4_as_np,
)
from ..utility import g4_units

# ! ======= KNOWN TODO'S ========
# ! - in MT mode, create_field_manager() is called per thread and overwrites shared instance attrs (g4_field, etc.),
# !   so any code that relies on those attributes being available later on will get an arbitrary thread's copy.
# !   Not sure if this is really an issue or not, but worth investigating.
# ! =============================


class FieldBase(GateObject):
    """Base class for electric and magnetic fields."""

    # hints for IDE
    stepper: str
    step_minimum: float
    delta_chord: float
    delta_one_step: float
    delta_intersection: float
    min_epsilon_step: float
    max_epsilon_step: float

    user_info_defaults = {
        "stepper": (
            "DormandPrince745",
            {
                "doc": (
                    "Integration stepper type. "
                    "General-purpose (any field): 'DormandPrince745' (default), 'ClassicalRK4', 'CashKarpRKF45', "
                    "'BogackiShampine45', 'BogackiShampine23', 'DormandPrinceRK56', "
                    "'DormandPrinceRK78'. "
                    "Magnetic-only: 'NystromRK4', 'ExactHelixStepper'."
                ),
            },
        ),
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
        self._g4_runtime_objects = []
        self._field_volume_obj: Any = None

        self.attached_to = []
        self._field_changes_energy = False

        # Integration objects - shared by all field subclasses
        self.g4_equation_of_motion = None
        self.g4_integrator_stepper = None
        self.g4_integration_driver = None
        self.g4_chord_finder = None

    @property
    def field_changes_energy(self) -> bool:
        """Whether the field changes particle energy (False for magnetic, True for others)."""
        return self._field_changes_energy

    def refresh_transforms(self) -> None:
        """Recompute and push cached world-to-local transforms after dynamic
        geometry changes.
        """
        for entry in self._g4_runtime_objects:
            volume = entry.get("volume")
            g4_field = entry.get("field")
            if volume is None or g4_field is None:
                continue

            g4_translations = []
            g4_rotations = []
            for i in range(volume.number_of_repetitions):
                pv = volume.get_g4_physical_volume(i)
                T = vec_g4_as_np(pv.GetObjectTranslation())
                rot = pv.GetObjectRotation()
                R = rot_g4_as_np(rot) if rot is not None else np.eye(3)
                for anc in volume.ancestor_volumes[::-1]:
                    # Ancestors are assumed to be singly placed, so we use idx 0
                    anc_pvs = getattr(anc, "g4_physical_volumes", None)
                    if not anc_pvs:
                        continue
                    anc_pv = anc_pvs[0]
                    anc_T = vec_g4_as_np(anc_pv.GetObjectTranslation())
                    anc_rot = anc_pv.GetObjectRotation()
                    anc_R = rot_g4_as_np(anc_rot) if anc_rot is not None else np.eye(3)
                    T = anc_R @ T + anc_T
                    R = anc_R @ R
                g4_translations.append(vec_np_as_g4(T))
                g4_rotations.append(rot_np_as_g4(R))

            g4_field.SetTransforms(g4_translations, g4_rotations)

    def create_field_manager(self, volume_obj) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        msg = "create_field_manager() must be implemented in subclasses."
        raise NotImplementedError(msg)

    def _make_g4_transforms(self):
        """Return (g4_translations, g4_rotations) for the current field volume."""
        translations_np, rotations_np = get_transform_world_to_local(
            self._field_volume_obj
        )
        return (
            [vec_np_as_g4(t) for t in translations_np],
            [rot_np_as_g4(r) for r in rotations_np],
        )

    def _validate_stepper(self) -> None:
        """Raise ValueError if the current stepper is incompatible with this field type."""
        if self.stepper not in _stepper_map:
            raise ValueError(
                f"Unknown stepper '{self.stepper}'. "
                f"Choose from {list(_stepper_map.keys())}."
            )
        if self.stepper in _magnetic_only_steppers and self.field_changes_energy:
            raise ValueError(
                f"Stepper '{self.stepper}' only supports pure magnetic fields. "
                "Choose a general-purpose stepper for electric or EM fields."
            )

    def _build_field_manager(
        self, inner_field, gate_field, equation_cls, n_vars, volume_obj
    ):
        """Build equation/stepper/driver/chord_finder/fm, record runtime objects, return fm."""
        self._validate_stepper()
        self.g4_field = gate_field
        self.g4_equation_of_motion = equation_cls(gate_field)
        stepper_factory = _stepper_map[self.stepper]
        self.g4_integrator_stepper = stepper_factory(self.g4_equation_of_motion, n_vars)
        self.g4_integration_driver = g4.G4MagInt_Driver(
            self.step_minimum, self.g4_integrator_stepper, n_vars, 0
        )
        self.g4_chord_finder = g4.G4ChordFinder(self.g4_integration_driver)
        self.g4_chord_finder.SetDeltaChord(self.delta_chord)

        fm = g4.G4FieldManager(
            gate_field, self.g4_chord_finder, self.field_changes_energy
        )
        fm.SetDeltaOneStep(self.delta_one_step)
        fm.SetDeltaIntersection(self.delta_intersection)
        fm.SetMinimumEpsilonStep(self.min_epsilon_step)
        fm.SetMaximumEpsilonStep(self.max_epsilon_step)

        # Keep all runtime objects alive for the full simulation lifetime.
        self._g4_runtime_objects.append(
            {
                "inner_field": inner_field,
                "field": gate_field,
                "equation": self.g4_equation_of_motion,
                "stepper": self.g4_integrator_stepper,
                "driver": self.g4_integration_driver,
                "chord_finder": self.g4_chord_finder,
                "field_manager": fm,
                "volume": volume_obj,
            }
        )

        return fm

    def to_dictionary(self):
        d = super().to_dictionary()
        d["attached_to"] = list(self.attached_to)
        return d

    def from_dictionary(self, d):
        super().from_dictionary(d)
        self.attached_to = d.get("attached_to", [])

    def close(self) -> None:
        self.g4_field = None
        self.g4_chord_finder = None
        self.g4_integration_driver = None
        self.g4_integrator_stepper = None
        self.g4_equation_of_motion = None
        self._g4_runtime_objects = []
        super().close()


class MagneticField(FieldBase):
    """Base class for magnetic fields."""

    def _create_inner_field(self):
        """Create and return the inner G4MagneticField in local volume coordinates.
        Override in subclasses."""
        raise NotImplementedError(
            "_create_inner_field() must be implemented in subclasses."
        )

    def create_field_manager(self, volume_obj) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        self._field_volume_obj = volume_obj
        inner = self._create_inner_field()
        g4_translations, g4_rotations = self._make_g4_transforms()
        gate_field = g4.GateMagneticField(
            inner,
            self._field_volume_obj.g4_solid,
            g4_translations,
            g4_rotations,
            self.delta_chord,
        )
        # TODO: allow user choice of stepper and equation type
        return self._build_field_manager(
            inner, gate_field, g4.G4Mag_UsualEqRhs, 6, volume_obj
        )


class UniformMagneticField(MagneticField):
    """Uniform magnetic field with constant field vector.

    field_vector is specified in the local coordinate frame of the attached
    volume.  For a non-rotated volume this is identical to the world frame.
    For a rotated volume the field direction rotates with the volume.
    """

    # hints for IDE
    field_vector: list

    user_info_defaults = {
        "field_vector": (
            [0, 0, 0],
            {
                "doc": "Field vector [Bx, By, Bz] in local volume coordinates. "
                "Each component in magnetic field strength units (e.g., Tesla).",
            },
        ),
    }

    def _create_inner_field(self):
        return g4.G4UniformMagField(g4.G4ThreeVector(*self.field_vector))


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

    def _create_inner_field(self):
        return g4.G4QuadrupoleMagField(self.gradient)


class SextupoleMagneticField(MagneticField):
    """Sextupole magnetic field with gradient."""

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

    def _create_inner_field(self):
        return g4.G4SextupoleMagField(self.gradient)


class CustomMagneticField(MagneticField):
    """Custom magnetic field defined by a Python callback function."""

    # hints for IDE
    field_function: callable

    user_info_defaults = {
        "field_function": (
            None,
            {
                "doc": "Python function that takes [x, y, z, t] and returns [Bx, By, Bz], all in local volume coordinates.",
            },
        ),
    }

    def _create_inner_field(self):
        """Create the custom magnetic field using the Python trampoline.

        field_function receives (x, y, z, t) in the local coordinate frame of
        the attached volume and must return [Bx, By, Bz] in that same local
        frame.  The base class rotates the result to world coordinates.
        """
        _validate_field_function(self.field_function, "CustomMagneticField", 3)

        class _PyMagneticField(g4.G4MagneticField):
            def __init__(inner_self, callback):
                super().__init__()
                inner_self._callback = callback

            def GetFieldValue(inner_self, point):
                return inner_self._callback(*point)

        return _PyMagneticField(self.field_function)

    def to_dictionary(self):
        raise NotImplementedError(
            "Custom fields with Python callbacks cannot be serialized."
        )


class ElectroMagneticField(FieldBase):
    """Base class for electromagnetic fields (includes pure electric)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Electromagnetic fields change particle energy
        self._field_changes_energy = True

    def _create_inner_field(self):
        """Create and return the inner G4ElectroMagneticField in local coordinates.
        Override in subclasses."""
        raise NotImplementedError(
            "_create_inner_field() must be implemented in subclasses."
        )

    def create_field_manager(self, volume_obj) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
        self._field_volume_obj = volume_obj
        inner = self._create_inner_field()
        g4_translations, g4_rotations = self._make_g4_transforms()
        gate_field = g4.GateElectroMagneticField(
            inner,
            self._field_volume_obj.g4_solid,
            g4_translations,
            g4_rotations,
            self.delta_chord,
        )
        # TODO: allow user choice of stepper and equation type
        # 8 variables: x,y,z + px,py,pz + t + E
        return self._build_field_manager(
            inner, gate_field, g4.G4EqMagElectricField, 8, volume_obj
        )


class ElectricField(ElectroMagneticField):
    """Base class for pure electric fields."""

    # _field_changes_energy is already True from ElectroMagneticField


class UniformElectricField(ElectricField):
    """Uniform electric field with constant field vector."""

    # hints for IDE
    field_vector: list

    user_info_defaults = {
        "field_vector": (
            [0, 0, 0],
            {
                "doc": "Field vector [Ex, Ey, Ez] in local volume coordinates. "
                "Each component in electric field strength units.",
            },
        ),
    }

    def _create_inner_field(self):
        return g4.G4UniformElectricField(g4.G4ThreeVector(*self.field_vector))


class CustomElectricField(ElectricField):
    """Custom electric field defined by a Python callback function."""

    # hints for IDE
    field_function: callable

    user_info_defaults = {
        "field_function": (
            None,
            {
                "doc": "Python function that takes [x, y, z, t] and returns [Ex, Ey, Ez], all in local volume coordinates.",
            },
        ),
    }

    def _create_inner_field(self):
        _validate_field_function(self.field_function, "CustomElectricField", 3)

        class _PyElectricField(g4.G4ElectricField):
            def __init__(inner_self, callback):
                super().__init__()
                inner_self._callback = callback

            def GetFieldValue(inner_self, point):
                return inner_self._callback(*point)

            def DoesFieldChangeEnergy(inner_self):
                return True

        return _PyElectricField(self.field_function)

    def to_dictionary(self):
        raise NotImplementedError(
            "Custom fields with Python callbacks cannot be serialized."
        )


class UniformElectroMagneticField(ElectroMagneticField):
    """Uniform electromagnetic field with constant magnetic and electric field vectors."""

    # hints for IDE
    field_vector_B: list
    field_vector_E: list

    user_info_defaults = {
        "field_vector_B": (
            [0, 0, 0],
            {
                "doc": "Magnetic field vector [Bx, By, Bz] in local volume coordinates.",
            },
        ),
        "field_vector_E": (
            [0, 0, 0],
            {
                "doc": "Electric field vector [Ex, Ey, Ez] in local volume coordinates.",
            },
        ),
    }

    def _create_inner_field(self):
        return g4.GateUniformElectroMagneticField(
            g4.G4ThreeVector(*self.field_vector_E),
            g4.G4ThreeVector(*self.field_vector_B),
        )


class CustomElectroMagneticField(ElectroMagneticField):
    """Custom electromagnetic field defined by a Python callback function."""

    # hints for IDE
    field_function: callable

    user_info_defaults = {
        "field_function": (
            None,
            {
                "doc": "Python function that takes [x, y, z, t] and returns [Bx, By, Bz, Ex, Ey, Ez], all in local volume coordinates.",
            },
        ),
    }

    def _create_inner_field(self):
        _validate_field_function(self.field_function, "CustomElectroMagneticField", 6)

        class _PyElectroMagneticField(g4.G4ElectroMagneticField):
            def __init__(inner_self, callback):
                super().__init__()
                inner_self._callback = callback

            def GetFieldValue(inner_self, point):
                return inner_self._callback(*point)

            def DoesFieldChangeEnergy(inner_self):
                return True

        return _PyElectroMagneticField(self.field_function)

    def to_dictionary(self):
        raise NotImplementedError(
            "Custom fields with Python callbacks cannot be serialized."
        )


# Helper function to parse field_matrix for mapped fields and extract grid parameters and field value arrays
def _parse_field_matrix(mat, class_name):
    """Parse a field matrix into grid parameters and sorted field value arrays.

    mat must be a 2D array with columns [x, y, z, Fx, Fy, Fz] on a
    regular Cartesian grid in Geant4 units, sorted in any order.

    Returns (nx, ny, nz, x0, y0, z0, dx, dy, dz, field_cols) where field_cols
    is a list of n_field_cols 1D arrays in lexicographical x->y->z order.
    """
    mat = np.asarray(mat, dtype=np.float64)
    expected_cols = 6
    if mat.ndim != 2 or mat.shape[1] != expected_cols:
        raise ValueError(
            f"{class_name}: field_matrix must be a 2D array with {expected_cols} "
            f"columns [x, y, z, Fx, Fy, Fz], "
            f"got shape {mat.shape}"
        )

    positions = mat[:, :3]
    field_values = mat[:, 3:]

    sort_idx = np.lexsort((positions[:, 2], positions[:, 1], positions[:, 0]))
    positions = positions[sort_idx]
    field_values = field_values[sort_idx]

    x_vals = np.unique(np.round(positions[:, 0], 10))
    y_vals = np.unique(np.round(positions[:, 1], 10))
    z_vals = np.unique(np.round(positions[:, 2], 10))
    nx, ny, nz = len(x_vals), len(y_vals), len(z_vals)

    if len(positions) != nx * ny * nz:
        raise ValueError(
            f"{class_name}: field_matrix does not define a complete regular 3D grid: "
            f"expected {nx}*{ny}*{nz}={nx * ny * nz} points, got {len(positions)}"
        )
    for axis, vals, label in ((x_vals, nx, "x"), (y_vals, ny, "y"), (z_vals, nz, "z")):
        if vals < 2:
            raise ValueError(
                f"{class_name}: field_matrix must have at least 2 unique points "
                f"along the {label}-axis"
            )
        if vals > 2 and not np.allclose(np.diff(axis), axis[1] - axis[0]):
            raise ValueError(
                f"{class_name}: field_matrix {label}-axis does not have uniform spacing"
            )

    x0, y0, z0 = float(x_vals[0]), float(y_vals[0]), float(z_vals[0])
    dx = float(x_vals[1] - x_vals[0])
    dy = float(y_vals[1] - y_vals[0])
    dz = float(z_vals[1] - z_vals[0])

    field_cols = [field_values[:, i] for i in range(3)]
    return nx, ny, nz, x0, y0, z0, dx, dy, dz, field_cols


# Helper function to validate user-provided field_function for custom fields
def _validate_field_function(
    func: Any,
    class_name: str,
    n_components: int,
) -> None:
    """Validate that field_function is a callable that returns the expected number of components."""
    if func is None:
        raise ValueError(f"field_function must be provided for {class_name}")
    if not callable(func):
        raise TypeError("field_function must be a callable function")
    result = list(func(0, 0, 0, 0))
    if len(result) != n_components:
        raise ValueError(
            f"{class_name}: field_function must return {n_components} components, "
            f"got {len(result)}"
        )


# Steppers that only work with pure magnetic fields
_magnetic_only_steppers = {"NystromRK4", "ExactHelixStepper"}

# Stepper factory
_stepper_map = {
    "DormandPrince745": lambda eq, n: g4.G4DormandPrince745(eq, n),
    "CashKarpRKF45": lambda eq, n: g4.G4CashKarpRKF45(eq, n),
    "BogackiShampine45": lambda eq, n: g4.G4BogackiShampine45(eq, n),
    "BogackiShampine23": lambda eq, n: g4.G4BogackiShampine23(eq, n),
    "DormandPrinceRK56": lambda eq, n: g4.G4DormandPrinceRK56(eq, n),
    "DormandPrinceRK78": lambda eq, n: g4.G4DormandPrinceRK78(eq, n),
    "ClassicalRK4": lambda eq, n: g4.G4ClassicalRK4(eq, n),
    "NystromRK4": lambda eq, n: g4.G4NystromRK4(eq),
    "ExactHelixStepper": lambda eq, n: g4.G4ExactHelixStepper(eq),
}

_interp_map = {
    "trilinear": g4.GateGridInterpolationMethod.Trilinear,
    "nearest": g4.GateGridInterpolationMethod.Nearest,
}

_mapped_field_user_info = {
    "field_matrix": (
        None,
        {
            "doc": (
                "2D numpy array on a regular Cartesian grid in Geant4 units. "
                "Structure: [[x, y, z, field components...], ...]. "
            ),
        },
    ),
    "interpolation": (
        "trilinear",
        {
            "doc": "Interpolation method: 'trilinear' (default) or 'nearest'.",
        },
    ),
}


class MappedMagneticField(MagneticField):
    """Magnetic field defined by values on a regular 3D Cartesian grid."""

    field_matrix: np.ndarray
    interpolation: str

    user_info_defaults = _mapped_field_user_info

    def create_field_manager(self, volume_obj) -> g4.G4FieldManager:
        if self.field_matrix is None:
            raise ValueError("field_matrix must be provided for MappedMagneticField")
        if self.interpolation not in _interp_map:
            raise ValueError(
                f"Unknown interpolation '{self.interpolation}'. "
                f"Choose 'trilinear' or 'nearest'."
            )
        self._field_volume_obj = volume_obj
        nx, ny, nz, x0, y0, z0, dx, dy, dz, (Bx, By, Bz) = _parse_field_matrix(
            self.field_matrix, "MappedMagneticField"
        )
        g4_translations, g4_rotations = self._make_g4_transforms()
        gate_field = g4.GateMappedMagneticField(
            self._field_volume_obj.g4_solid,
            g4_translations,
            g4_rotations,
            self.delta_chord,
            nx,
            ny,
            nz,
            x0,
            y0,
            z0,
            dx,
            dy,
            dz,
            Bx,
            By,
            Bz,
            _interp_map[self.interpolation],
        )
        return self._build_field_manager(
            None, gate_field, g4.G4Mag_UsualEqRhs, 6, volume_obj
        )


class MappedElectricField(ElectricField):
    """Electric field defined by values on a regular 3D Cartesian grid."""

    field_matrix: np.ndarray
    interpolation: str

    user_info_defaults = _mapped_field_user_info

    def create_field_manager(self, volume_obj) -> g4.G4FieldManager:
        if self.field_matrix is None:
            raise ValueError("field_matrix must be provided for MappedElectricField")
        if self.interpolation not in _interp_map:
            raise ValueError(
                f"Unknown interpolation '{self.interpolation}'. "
                f"Choose 'trilinear' or 'nearest'."
            )
        self._field_volume_obj = volume_obj
        nx, ny, nz, x0, y0, z0, dx, dy, dz, (Ex, Ey, Ez) = _parse_field_matrix(
            self.field_matrix, "MappedElectricField"
        )
        g4_translations, g4_rotations = self._make_g4_transforms()
        gate_field = g4.GateMappedElectricField(
            self._field_volume_obj.g4_solid,
            g4_translations,
            g4_rotations,
            self.delta_chord,
            nx,
            ny,
            nz,
            x0,
            y0,
            z0,
            dx,
            dy,
            dz,
            Ex,
            Ey,
            Ez,
            _interp_map[self.interpolation],
        )
        return self._build_field_manager(
            None, gate_field, g4.G4EqMagElectricField, 8, volume_obj
        )


class MappedElectroMagneticField(ElectroMagneticField):
    """Electromagnetic field with separate B and E grids on regular 3D Cartesian grids.

    field_matrix_B and field_matrix_E must have columns [x, y, z, Bx, By, Bz]
    and [x, y, z, Ex, Ey, Ez] respectively, in Geant4 units.
    Field lookup is performed entirely in C++ using trilinear or nearest-neighbour
    interpolation, with B and E computed independently on their respective grids.
    """

    field_matrix_B: np.ndarray
    field_matrix_E: np.ndarray
    interpolation: str

    user_info_defaults = {
        "field_matrix_B": (
            None,
            {
                "doc": (
                    "2D numpy array on a regular Cartesian grid in Geant4 units. "
                    "Columns: [x, y, z, Bx, By, Bz]."
                ),
            },
        ),
        "field_matrix_E": (
            None,
            {
                "doc": (
                    "2D numpy array on a regular Cartesian grid in Geant4 units. "
                    "Columns: [x, y, z, Ex, Ey, Ez]."
                ),
            },
        ),
        "interpolation": (
            "trilinear",
            {
                "doc": "Interpolation method: 'trilinear' (default) or 'nearest'.",
            },
        ),
    }

    def create_field_manager(self, volume_obj) -> g4.G4FieldManager:
        if self.field_matrix_B is None:
            raise ValueError(
                "field_matrix_B must be provided for MappedElectroMagneticField"
            )
        if self.field_matrix_E is None:
            raise ValueError(
                "field_matrix_E must be provided for MappedElectroMagneticField"
            )
        if self.interpolation not in _interp_map:
            raise ValueError(
                f"Unknown interpolation '{self.interpolation}'. "
                f"Choose 'trilinear' or 'nearest'."
            )
        self._field_volume_obj = volume_obj
        nx_B, ny_B, nz_B, x0_B, y0_B, z0_B, dx_B, dy_B, dz_B, (Bx, By, Bz) = (
            _parse_field_matrix(
                self.field_matrix_B, "MappedElectroMagneticField (B grid)"
            )
        )
        nx_E, ny_E, nz_E, x0_E, y0_E, z0_E, dx_E, dy_E, dz_E, (Ex, Ey, Ez) = (
            _parse_field_matrix(
                self.field_matrix_E, "MappedElectroMagneticField (E grid)"
            )
        )
        g4_translations, g4_rotations = self._make_g4_transforms()
        gate_field = g4.GateMappedElectroMagneticField(
            self._field_volume_obj.g4_solid,
            g4_translations,
            g4_rotations,
            self.delta_chord,
            nx_B,
            ny_B,
            nz_B,
            x0_B,
            y0_B,
            z0_B,
            dx_B,
            dy_B,
            dz_B,
            Bx,
            By,
            Bz,
            nx_E,
            ny_E,
            nz_E,
            x0_E,
            y0_E,
            z0_E,
            dx_E,
            dy_E,
            dz_E,
            Ex,
            Ey,
            Ez,
            _interp_map[self.interpolation],
        )
        return self._build_field_manager(
            None, gate_field, g4.G4EqMagElectricField, 8, volume_obj
        )


field_types = {
    "UniformMagneticField": UniformMagneticField,
    "QuadrupoleMagneticField": QuadrupoleMagneticField,
    "SextupoleMagneticField": SextupoleMagneticField,
    "CustomMagneticField": CustomMagneticField,
    "MappedMagneticField": MappedMagneticField,
    "UniformElectricField": UniformElectricField,
    "CustomElectricField": CustomElectricField,
    "MappedElectricField": MappedElectricField,
    "UniformElectroMagneticField": UniformElectroMagneticField,
    "CustomElectroMagneticField": CustomElectroMagneticField,
    "MappedElectroMagneticField": MappedElectroMagneticField,
}

process_cls(FieldBase)
process_cls(MagneticField)
process_cls(UniformMagneticField)
process_cls(QuadrupoleMagneticField)
process_cls(SextupoleMagneticField)
process_cls(CustomMagneticField)
process_cls(MappedMagneticField)
process_cls(ElectroMagneticField)
process_cls(ElectricField)
process_cls(UniformElectricField)
process_cls(CustomElectricField)
process_cls(MappedElectricField)
process_cls(UniformElectroMagneticField)
process_cls(CustomElectroMagneticField)
process_cls(MappedElectroMagneticField)
