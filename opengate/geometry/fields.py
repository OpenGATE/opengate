from ..base import GateObject

import opengate_core as g4



class FieldBase(GateObject):
    # Base class for electric and magnetic fields

    field_type: str
    attached_to: list[str]

    g4_field: g4.G4Field

    # TODO: implement the user info defaults
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class MagneticField(FieldBase):
    # Base class for electric and magnetic fields

    g4_equation_of_motion: g4.G4Mag_UsualEqRhs
    g4_integrator_stepper: g4.G4MagIntegratorStepper
    g4_chord_finder: g4.G4ChordFinder

    user_info_defaults = {
        ""
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.field_type = "MagneticField"


