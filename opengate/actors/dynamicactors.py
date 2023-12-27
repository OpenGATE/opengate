import opengate_core as g4

from ..definitions import __world_name__
from ..base import GateObject
from ..geometry.utility import rot_np_as_g4, vec_np_as_g4
from .base import ActorBase


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

    def initialize(self, simulation_engine_wr=None):
        super().initialize(simulation_engine_wr)
        for c in self.user_info.geometry_changers:
            c.initialize()

    def BeginOfRunActionMasterThread(self, run_id):
        print("DEBUG: DynamicGeometryactor.BeginOfRunActionMasterThread")
        gm = g4.G4GeometryManager.GetInstance()
        gm.OpenGeometry(None)
        for c in self.user_info.geometry_changers:
            c.apply_change(run_id)
        gm.CloseGeometry(True, False, None)


def _setter_hook_attached_to(self, value):
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

    def __init__(self, *args, simulation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.simulation = simulation

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
        vol = self.simulation.volume_manager.get_volume(self.attached_to)
        vol.update_label_image(self.label_image[self.images[run_id]])
        print(f"DEBUG: Updated image in volume {vol.name}. Run ID: {run_id}.")


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

    def initialize(self):
        self.g4_translations = []
        for t in self.translations:
            self.g4_translations.append(vec_np_as_g4(t))

    def apply_change(self, run_id):
        # This should better go in initialize, but the initialize() is called before the RunManager is initialized
        # so the physical volumes do not yet exist.
        # FIXME: revisit after source/actor refactoring
        if self.g4_physical_volume is None:
            vol = self.simulation.volume_manager.get_volume(self.attached_to)
            self.g4_physical_volume = vol.get_g4_physical_volume(self.repetition_index)
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
            vol = self.simulation.volume_manager.get_volume(self.attached_to)
            self.g4_physical_volume = vol.get_g4_physical_volume(self.repetition_index)
        self.g4_physical_volume.SetRotation(self.g4_rotations[run_id])
