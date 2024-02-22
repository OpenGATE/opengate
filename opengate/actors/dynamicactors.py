import opengate_core as g4

from ..definitions import __world_name__
from ..base import GateObject
from ..geometry.utility import rot_np_as_g4, vec_np_as_g4
from ..exception import fatal
from .base import ActorBase
from ..decorators import requires_fatal


class DynamicGeometryActor(g4.GateVActor, ActorBase):
    type_name = "DynamicGeometryActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.geometry_changers = []  # will become obsolete after actor refactoring

    def __init__(self, user_info):
        user_info.mother = __world_name__
        ActorBase.__init__(self, user_info)
        g4.GateVActor.__init__(self, user_info.__dict__)
        self.AddActions({"BeginOfRunActionMasterThread"})

    def close(self):
        for c in self.user_info.geometry_changers:
            c.close()
        super().close()

    def initialize(self, simulation_engine_wr=None):
        super().initialize(simulation_engine_wr)
        for c in self.user_info.geometry_changers:
            if c.volume_manager is None:
                c.volume_manager = self.simulation.volume_manager
            c.initialize()

    # such as method will work after actor refactoring
    # def add_geometry_changer(self, changer):
    #     """Add geometry changer(s) to the actor. Input can be a single changer or a list of changers.
    #     """
    #     self.geometry_changers.extend(list(changer))

    def BeginOfRunActionMasterThread(self, run_id):
        gm = g4.G4GeometryManager.GetInstance()
        gm.OpenGeometry(None)
        for c in self.user_info.geometry_changers:
            c.apply_change(run_id)
        gm.CloseGeometry(True, False, None)


def _setter_hook_attached_to(self, value):
    # try to pick up the volume_manager from the attached_to volume
    try:
        volume_manager = value.volume_manager
    except AttributeError:
        volume_manager = None
    if (
        self.volume_manager is not None
        and volume_manager is not None
        and self.volume_manager is not volume_manager
    ):
        fatal(
            f"The volume_manager of the changers is different from the volume_manager which manages the attached_to volume. "
        )
    if volume_manager is not None:
        self.volume_manager = volume_manager
    try:
        return value.name
    except AttributeError:
        return value


class GeometryChanger(GateObject):
    user_info_defaults = {
        "attached_to": (
            None,
            {
                "doc": "The object which this changer handles, e.g. a volume.",
                "setter_hook": _setter_hook_attached_to,
            },
        ),
    }

    def __init__(self, *args, volume_manager=None, **kwargs):
        self.volume_manager = None
        super().__init__(*args, **kwargs)
        # the user might have passed an 'attached_to' keyword argument pointing to a Volume object
        # in that case, the volume_manager was picked up from the volume
        # check for consistency
        if (
            self.volume_manager is not None
            and volume_manager is not None
            and self.volume_manager is not volume_manager
        ):
            fatal(
                f"The volume_manager passed as keyword argument is different "
                f"from the volume_manager which manages the attached_to volume. "
            )
        if volume_manager is not None:
            self.volume_manager = volume_manager

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
        self.g4_translations = []
        for t in self.translations:
            self.g4_translations.append(vec_np_as_g4(t))

    def apply_change(self, run_id):
        # This should better go in initialize, but the initialize() is called before the RunManager is initialized
        # so the physical volumes do not yet exist.
        # FIXME: revisit after source/actor refactoring
        if self.g4_physical_volume is None:
            self.g4_physical_volume = self.attached_to_volume.get_g4_physical_volume(
                self.repetition_index
            )
        self.g4_physical_volume.SetTranslation(self.g4_translations[run_id])


class VolumeRotationChanger(GeometryChanger):
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
        self.g4_rotations = []
        for r in self.rotations:
            g4_rot = rot_np_as_g4(r)
            g4_rot.invert()
            g4_rot.rep3x3()
            self.g4_rotations.append(g4_rot)

    def apply_change(self, run_id):
        # This should better go in initialize, but the initialize() is called before the RunManager is initialized
        # so the physical volumes do not yet exist.
        # FIXME: revisit after source/actor refactoring
        if self.g4_physical_volume is None:
            self.g4_physical_volume = self.attached_to_volume.get_g4_physical_volume(
                self.repetition_index
            )
        self.g4_physical_volume.SetRotation(self.g4_rotations[run_id])
