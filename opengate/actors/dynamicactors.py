from typing import Optional

import opengate_core as g4
from ..definitions import __world_name__
from ..base import GateObject
from ..geometry.utility import rot_np_as_g4, vec_np_as_g4
from ..exception import fatal
from .base import ActorBase
from ..decorators import requires_fatal


class DynamicGeometryActor(ActorBase, g4.GateVActor):

    def __init__(self, *args, **kwargs):
        kwargs["attached_to"] = __world_name__
        ActorBase.__init__(self, *args, **kwargs)
        self.geometry_changers = []
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateVActor.__init__(self, {"name": self.name})
        self.AddActions({"BeginOfRunActionMasterThread"})

    def close(self):
        for c in self.geometry_changers:
            c.close()
        self.geometry_changers = []
        super().close()

    def to_dictionary(self):
        return_dict = super().to_dictionary()
        return_dict["geometry_changers"] = dict(
            [(v.name, v.to_dictionary()) for v in self.geometry_changers]
        )
        return return_dict

    def initialize(self):
        ActorBase.initialize(self)
        for c in self.geometry_changers:
            if c.volume_manager is None:
                c.volume_manager = self.simulation.volume_manager
            c.initialize()

    def BeginOfRunActionMasterThread(self, run_id):
        gm = g4.G4GeometryManager.GetInstance()
        gm.OpenGeometry(None)
        for c in self.geometry_changers:
            c.apply_change(run_id)
        gm.CloseGeometry(True, False, None)


def _setter_hook_attached_to(self, value):
    # try to pick up the simulation from the attached_to volume
    try:
        simulation = value.simulation
    except AttributeError:
        simulation = None
    if (
        self.simulation is not None
        and simulation is not None
        and self.simulation is not simulation
    ):
        fatal(
            f"The simulation of the changers is different from the simulation "
            f"which manages the attached_to volume. "
        )
    if simulation is not None:
        self.simulation = simulation
    try:
        return value.name
    except AttributeError:
        return value


class GeometryChanger(GateObject):

    # hints for IDE
    attached_to: Optional[str]

    user_info_defaults = {
        "attached_to": (
            None,
            {
                "doc": "The object which this changer handles, e.g. a volume.",
                "setter_hook": _setter_hook_attached_to,
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        # FIXME: update this considering that GateObject now holds a ref to simulation
        simulation = kwargs.pop(
            "simulation", None
        )  # intercept simulation from kwargs if present
        super().__init__(*args, **kwargs)

        # the user might have passed an 'attached_to' keyword argument pointing to a Volume object
        # in that case, the simulation was picked up from the volume
        # check for consistency
        if (
            self.simulation is not None
            and simulation is not None
            and self.simulation is not simulation
        ):
            fatal(
                f"The simulation passed as keyword argument is different "
                f"from the simulation which manages the attached_to volume. "
            )
        if simulation is not None:
            self.simulation = simulation

    @property
    def volume_manager(self):
        if self.simulation is not None:
            return self.simulation.volume_manager
        else:
            return None

    @property
    @requires_fatal("volume_manager")
    def attached_to_volume(self):
        return self.volume_manager.get_volume(self.attached_to)

    def initialize(self):
        # dummy implementation - nothing to do in the general case
        pass

    def apply_change(self, run_id):
        raise NotImplementedError(
            f"You are trying to call the method in the base class {type(self)}, "
            f"but it is only available in classes inheriting from it. "
        )


class VolumeImageChanger(GeometryChanger):

    # hints for IDE
    images: Optional[list]
    label_image: Optional[dict]

    user_info_defaults = {
        "images": (
            None,
            {
                "doc": "List of image names corresponding to the run timing intervals. ",
            },
        ),
        "label_image": (
            None,
            {
                "doc": "Dictionary of label images where the keys correspond to the image names "
                "stored in the user info 'images'.",
            },
        ),
    }

    def apply_change(self, run_id):
        self.attached_to_volume.update_label_image(
            self.label_image[self.images[run_id]]
        )


class VolumeTranslationChanger(GeometryChanger):

    # hints for IDE
    translations: Optional[list]
    repetition_index: int

    user_info_defaults = {
        "translations": (
            None,
            {
                "doc": "The list of translations corresponding to the run timing intervals. ",
            },
        ),
        "repetition_index": (
            0,
            {
                "doc": "The copy index of the G4PhysicalVolume to which the translations are applied. ",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.g4_translations = []
        self.g4_physical_volume = None

    def close(self):
        self.g4_translations = []
        self.g4_physical_volume = None
        super().close()

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_translations"] = None
        return_dict["g4_physical_volume"] = None
        return return_dict

    def initialize(self):
        self.g4_physical_volume = self.attached_to_volume.get_g4_physical_volume(
            self.repetition_index
        )

        self.g4_translations = []
        for t in self.translations:
            self.g4_translations.append(vec_np_as_g4(t))

    def apply_change(self, run_id):
        self.g4_physical_volume.SetTranslation(self.g4_translations[run_id])


class VolumeRotationChanger(GeometryChanger):

    # hints for IDE
    rotations: Optional[list]
    repetition_index: int

    user_info_defaults = {
        "rotations": (
            None,
            {
                "doc": "The list of rotations corresponding to the run timing intervals. ",
            },
        ),
        "repetition_index": (
            0,
            {
                "doc": "The copy index of the G4PhysicalVolume to which the translations are applied. ",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.g4_rotations = []
        self.g4_physical_volume = None
        self.r = []

    def close(self):
        self.g4_rotations = []
        self.g4_physical_volume = None
        super().close()

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_rotations"] = None
        return_dict["g4_physical_volume"] = None
        return return_dict

    def initialize(self):
        self.g4_physical_volume = self.attached_to_volume.get_g4_physical_volume(
            self.repetition_index
        )

        self.g4_rotations = []
        for r in self.rotations:
            g4_rot = rot_np_as_g4(r)
            g4_rot.invert()
            self.g4_rotations.append(g4_rot.rep3x3())

    def apply_change(self, run_id):
        self.g4_physical_volume.SetRotationHepRep3x3(self.g4_rotations[run_id])
