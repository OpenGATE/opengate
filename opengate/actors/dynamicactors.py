import opengate_core as g4

from ..exception import fatal
from ..definitions import __world_name__
from ..base import GateObject
from ..geometry.utility import rot_np_as_g4, vec_np_as_g4
from .base import ActorBase


class DynamicGeometryActor(g4.GateVActor, ActorBase):
    def __init__(self, user_info):
        user_info["mother"] = __world_name__
        ActorBase.__init__(self, user_info)
        g4.GateVActor.__init__(self, user_info.__dict__)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})
        self.geometry_changers = []

    def add_changer(self, changer):
        if isinstance(changer, GeometryChanger):
            self.geometry_changers.append(changer)
        else:
            fatal(f"Error in {type(self)}: Invalid changer type {type(changer)}. ")

    def initialize(self, simulation_engine_wr=None):
        super().initialize(simulation_engine_wr)
        for c in self.geometry_changers:
            c.initialize()

    def BeginOfRunActionMasterThread(self, run_id):
        gm = g4.G4GeometryManager.GetInstance()
        gm.OpenGeometry()
        for c in self.geometry_changers:
            c.apply_change(run_id)
        gm.CloseGeometry(True, False, None)


def _setter_hook_attached_to(self, value):
    try:
        self.user_info["attached_to"] = value.name
    except AttributeError:
        self.user_info["attached_to"] = value


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

    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)
        self.changer_params = {}
        # ... this is a list of dictionaries, where each dictionary represents one set of parameters to be updated.
        # It is polulated by the initialize_dynamic_parametrisation() method
        # of the dynamic volume handled by this changer.

    def apply_change(self, run_id):
        raise NotImplementedError(
            f"You are trying to call the method in the base class {type(self)}, "
            f"but it is only available in classes inheriting from it. "
        )


class VolumeMover(GeometryChanger):
    def initialize(self):
        # get the volume object given its name
        vol = self.simulation.volume_manager.get_volume(self.attached_to)
        if "repetition_index" not in self.changer_params:
            fatal(
                f"Incompatible parameters found in the {type(self).__name__} of volume {vol.name}. "
                f"repetition_index is missing. "
            )
        self.changer_params["g4_phys_vol_name"] = vol.get_repetition_name_from_index(
            self.changer_params["repetition_index"]
        )
        if "rotation" in self.changer_params:
            g4_rotations = []
            for r in self.changer_params["rotation"]:
                g4_rot = rot_np_as_g4(r)
                g4_rot.invert()
                g4_rot.rep3x3()
                g4_rotations.append(g4_rot)
            self.changer_params["g4_rotations"] = g4_rotations
        if "translation" in self.changer_params:
            g4_translations = []
            for t in self.changer_params["translation"]:
                g4_translations.append(vec_np_as_g4(t))
            self.changer_params["g4_translations"] = g4_translations

    def apply_change(self, run_id):
        vol = self.simulation.volume_manager.get_volume(self.attached_to)

        try:
            physical_volume = vol.g4_physical_volumes[
                self.changer_params["repetition_index"]
            ]
        except IndexError:
            fatal(
                f"No physical volume with repetition index {self.changer_params['repetition_index']} found in volume {vol.name}. "
            )

        if "g4_rotations" in self.changer_params:
            try:
                g4_rot = self.changer_params["g4_rotations"][run_id]
            except IndexError:
                fatal(
                    f"No g4_rotation found for run ID {run_id} in the {type(self).__name__} of volume {vol.name}."
                )
            physical_volume.SetRotation(g4_rot)

        if "g4_translations" in self.changer_params:
            try:
                g4_trans = self.changer_params["g4_translations"][run_id]
            except IndexError:
                fatal(
                    f"No g4_translation found for run ID {run_id} in the {type(self).__name__} of volume {vol.name}."
                )
            physical_volume.SetTranslation(g4_trans)
