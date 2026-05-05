from typing import Any

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
# ! - implement the possibility of choosing the stepper type and equation type
# ! - bind the sextupole magnetic field geant4 implementation
# ! WIP - implement mapped fields (e.g., from a CSV file)
# ! - Overhead for custom fields implementation: every GetFieldValue call crosses c++ -> Python -> c++, acquiring the GIL each time,
# !   which is very inefficient. Need to implement a more efficient way on the C++ side.
# ! - in MT mode, create_field_manager() is called per thread and overwrites shared instance attrs (g4_field, etc.),
# !   so any code that relies on those attributes being available later on will get an arbitrary thread's copy.
# !   Not sure if this is really an issue or not, but worth investigating.
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
        self._g4_runtime_objects = []
        self._field_volume_obj: Any = (
            None  # set by engines.py before create_field_manager() is called
        )

        self.attached_to = []
        self._field_changes_energy = False

        # Integration objects — shared by all field subclasses
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
                R = rot_g4_as_np(pv.GetObjectRotation())
                for anc in volume.ancestor_volumes[::-1]:
                    anc_pv = getattr(anc, "g4_physical_volume", None)
                    if anc_pv is None:
                        continue
                    anc_T = vec_g4_as_np(anc_pv.GetObjectTranslation())
                    anc_R = rot_g4_as_np(anc_pv.GetObjectRotation())
                    T = anc_R @ T + anc_T
                    R = anc_R @ R
                g4_translations.append(vec_np_as_g4(T))
                g4_rotations.append(rot_np_as_g4(R))

            g4_field.SetTransforms(g4_translations, g4_rotations)

    def create_field_manager(self) -> g4.G4FieldManager:
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

    @staticmethod
    def _validate_field_function(func, class_name, n_components):
        """Validate that func is callable and returns exactly n_components values."""
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

    def _build_field_manager(self, inner_field, gate_field, equation_cls, n_vars):
        """Build equation/stepper/driver/chord_finder/fm, record runtime objects, return fm."""
        self.g4_field = gate_field
        self.g4_equation_of_motion = equation_cls(gate_field)
        self.g4_integrator_stepper = g4.G4ClassicalRK4(
            self.g4_equation_of_motion, n_vars
        )
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

    def create_field_manager(self) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
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
        return self._build_field_manager(inner, gate_field, g4.G4Mag_UsualEqRhs, 6)


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
                "doc": "Python function that takes [x, y, z, t] and returns [Bx, By, Bz].",
            },
        ),
    }

    def _create_inner_field(self):
        """Create the custom magnetic field using the Python trampoline.

        field_function receives (x, y, z, t) in the local coordinate frame of
        the attached volume and must return [Bx, By, Bz] in that same local
        frame.  The base class rotates the result to world coordinates.
        """
        self._validate_field_function(self.field_function, "CustomMagneticField", 3)

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

    def create_field_manager(self) -> g4.G4FieldManager:
        """Construct the field and return a configured G4FieldManager."""
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
        return self._build_field_manager(inner, gate_field, g4.G4EqMagElectricField, 8)


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
                "doc": "Python function that takes [x, y, z, t] and returns [Ex, Ey, Ez].",
            },
        ),
    }

    def _create_inner_field(self):
        self._validate_field_function(self.field_function, "CustomElectricField", 3)

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
    magnetic_field_vector: list
    electric_field_vector: list

    user_info_defaults = {
        "magnetic_field_vector": (
            [0, 0, 0],
            {
                "doc": "Magnetic field vector [Bx, By, Bz] in local volume coordinates.",
            },
        ),
        "electric_field_vector": (
            [0, 0, 0],
            {
                "doc": "Electric field vector [Ex, Ey, Ez] in local volume coordinates.",
            },
        ),
    }

    def _create_inner_field(self):
        return g4.GateUniformElectroMagneticField(
            g4.G4ThreeVector(*self.electric_field_vector),
            g4.G4ThreeVector(*self.magnetic_field_vector),
        )


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

    def _create_inner_field(self):
        self._validate_field_function(
            self.field_function, "CustomElectroMagneticField", 6
        )

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


# class MappedMagneticField(MagneticField):
#     """Magnetic field defined by values on a regular 3D Cartesian grid.

#     Field lookup is performed entirely in C++ (no Python callbacks at tracking
#     time) using either trilinear or nearest-neighbour interpolation. Points
#     outside the grid extent return zero field.
#     """

#     # ! TODO's (@srmarcballestero):
#     # ! - refactor the _create_field() function to make it simpler.
#     # ! - warning when using nearest interpolation with coarse grids
#     # ! - implement a MappedElectroMagneticField, and MappedElectricField.
#     # !    + for the electromagnetic case, separate grids should be used.
#     # !    + a mother class should abstract the core functionality.

#     # hints for IDE
#     field_matrix: np.ndarray
#     interpolation: str

#     user_info_defaults = {
#         "field_matrix": (
#             None,
#             {
#                 "doc": (
#                     "2D numpy array of shape (N, 6) with columns [x, y, z, Bx, By, Bz] "
#                     "on a regular Cartesian grid. Geant4 units should be used."
#                 ),
#             },
#         ),
#         "interpolation": (
#             "trilinear",
#             {
#                 "doc": "Interpolation method: 'trilinear' (default) or 'nearest'.",
#             },
#         ),
#     }

#     def __init__(self, *args, **kwargs) -> None:
#         super().__init__(*args, **kwargs)

#     def _create_field(self) -> None:
#         if self.field_matrix is None:
#             raise ValueError("field_matrix must be provided for MappedMagneticField")

#         mat = np.asarray(self.field_matrix, dtype=np.float64)
#         if mat.ndim != 2 or mat.shape[1] != 6:
#             raise ValueError(
#                 "field_matrix must be a 2D array with shape (N, 6) "
#                 "containing columns [x, y, z, Bx, By, Bz]"
#             )

#         # Separate coordinates and field values
#         positions = mat[:, :3]
#         B_values = mat[:, 3:]

#         # Sort in lexicographical order: x slowest, z fastest — matches C++ flat index.
#         sort_idx = np.lexsort((positions[:, 2], positions[:, 1], positions[:, 0]))
#         positions = positions[sort_idx]
#         B_values = B_values[sort_idx]

#         # Round to suppress floating-point noise before uniqueness check.
#         x_vals = np.unique(np.round(positions[:, 0], 10))
#         y_vals = np.unique(np.round(positions[:, 1], 10))
#         z_vals = np.unique(np.round(positions[:, 2], 10))
#         nx, ny, nz = len(x_vals), len(y_vals), len(z_vals)

#         # --- Grid validation ---
#         if len(positions) != nx * ny * nz:
#             raise ValueError(
#                 f"field_matrix does not define a complete regular 3D grid: "
#                 f"expected {nx}*{ny}*{nz}={nx * ny * nz} points, got {len(positions)}"
#             )
#         if nx > 2 and not np.allclose(np.diff(x_vals), x_vals[1] - x_vals[0]):
#             raise ValueError("field_matrix x-axis does not have uniform spacing")
#         if ny > 2 and not np.allclose(np.diff(y_vals), y_vals[1] - y_vals[0]):
#             raise ValueError("field_matrix y-axis does not have uniform spacing")
#         if nz > 2 and not np.allclose(np.diff(z_vals), z_vals[1] - z_vals[0]):
#             raise ValueError("field_matrix z-axis does not have uniform spacing")
#         if nx < 2 or ny < 2 or nz < 2:
#             raise ValueError(
#                 "field_matrix must have at least 2 unique points along each axis "
#                 "(no degenerate axes allowed)"
#             )
#         # ----------------------

#         x0, y0, z0 = float(x_vals[0]), float(y_vals[0]), float(z_vals[0])
#         dx = float(x_vals[1] - x_vals[0])
#         dy = float(y_vals[1] - y_vals[0])
#         dz = float(z_vals[1] - z_vals[0])

#         interp_map = {
#             "trilinear": g4.GateMappedMagneticFieldInterpolation.Trilinear,
#             "nearest": g4.GateMappedMagneticFieldInterpolation.Nearest,
#         }
#         if self.interpolation not in interp_map:
#             raise ValueError(
#                 f"Unknown interpolation '{self.interpolation}'. "
#                 f"Available options are 'trilinear' or 'nearest'."
#             )

#         # Collect one local-to-world transform per physical placement.
#         translations_np, rotations_np = get_transform_world_to_local(
#             self._field_volume_obj
#         )

#         g4_translations = [vec_np_as_g4(t) for t in translations_np]
#         g4_rotations = [rot_np_as_g4(r) for r in rotations_np]

#         self.g4_field = g4.GateMappedMagneticField(
#             B_values[:, 0], B_values[:, 1], B_values[:, 2],
#             nx, ny, nz,
#             x0, y0, z0,
#             dx, dy, dz,
#             interp_map[self.interpolation],
#             g4_translations, g4_rotations,
#         )

#     # Serialization
#     # def to_dictionary(self):
#     #     d = super().to_dictionary()
#     #     if self.field_matrix is not None:
#     #         d["field_matrix"] = np.asarray(self.field_matrix).tolist()
#     #     return d

#     # def from_dictionary(self, d):
#     #     super().from_dictionary(d)
#     #     if "field_matrix" in d and d["field_matrix"] is not None:
#     #         self.field_matrix = np.asarray(d["field_matrix"])


field_types = {
    "UniformMagneticField": UniformMagneticField,
    "QuadrupoleMagneticField": QuadrupoleMagneticField,
    "CustomMagneticField": CustomMagneticField,
    # "MappedMagneticField": MappedMagneticField,
    "UniformElectricField": UniformElectricField,
    "CustomElectricField": CustomElectricField,
    "UniformElectroMagneticField": UniformElectroMagneticField,
    "CustomElectroMagneticField": CustomElectroMagneticField,
}

process_cls(FieldBase)
process_cls(MagneticField)
process_cls(UniformMagneticField)
process_cls(QuadrupoleMagneticField)
process_cls(CustomMagneticField)
# process_cls(MappedMagneticField)
process_cls(ElectroMagneticField)
process_cls(ElectricField)
process_cls(UniformElectricField)
process_cls(CustomElectricField)
process_cls(UniformElectroMagneticField)
process_cls(CustomElectroMagneticField)
