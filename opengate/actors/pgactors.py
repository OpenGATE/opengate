import opengate_core as g4
from ..exception import fatal
from ..utility import g4_units
from ..base import process_cls
from .actoroutput import (
    ActorOutputSingleImageOfHistogram,
    UserInterfaceToActorOutputImage,
)

from .doseactors import VoxelDepositActor


class VoxelizedPromptGammaTLEActor(
    VoxelDepositActor, g4.GateVoxelizedPromptGammaTLEActor
):
    """
    FIXME doc todo
    """

    user_info_defaults = {
        "timebins": (
            200,
            {
                "doc": "Number of bins in the histogram for time",
            },
        ),
        "timerange": (
            5 * g4_units.ns,
            {
                "doc": "Range of the histogram in ns",
            },
        ),
        "energybins": (
            250,
            {
                "doc": "Number of bins in the histogram for energy",
            },
        ),
        "energyrange": (
            200 * g4_units.MeV,
            {
                "doc": "Range of the histogram in MeV",
            },
        ),
        "weight": (
            True,
            {
                "doc": "if the ToF spectra is weighted or not",
            },
        ),
        "vect_p": (
            None,
            {
                "doc": "Vector of weights for proton ToF deposition.",
            },
        ),
        "vect_n": (
            None,
            {
                "doc": "Vector of weights for neutron ToF deposition.",
            },
        ),
    }

    user_output_config = {
        "p_E": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "prot_E": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": True,
                },
            },
        },
        "p_tof": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "prot_tof": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": False,
                },
            },
        },
        "n_E": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "neutr_E": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": False,
                },
            },
        },
        "n_tof": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "neutr_tof": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": False,
                },
            },
        },
    }

    def __init__(self, *args, **kwargs):

        VoxelDepositActor.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):

        g4.GateVoxelizedPromptGammaTLEActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "BeginOfEventAction",
                "BeginOfRunAction",
                "SteppingAction",
                "EndOfRunAction",
                "EndOfRunActionMasterThread",
            }
        )

    def initialize(self, *args):

        self.check_user_input()
        VoxelDepositActor.initialize(self)

        if not (self.user_output.p_E.get_active(item=0)):
            self.user_output.p_E.set_write_to_disk(False, item=0)
        if not (self.user_output.p_tof.get_active(item=0)):
            self.user_output.p_tof.set_write_to_disk(False, item=0)
        if not (self.user_output.n_E.get_active(item=0)):
            self.user_output.n_E.set_write_to_disk(False, item=0)
        if not (self.user_output.n_tof.get_active(item=0)):
            self.user_output.n_tof.set_write_to_disk(False, item=0)

        self.InitializeUserInfo(self.user_info)

        self.SetProtonEnergyFlag(self.user_output.p_E.get_active(item=0))
        self.SetProtonTimeFlag(self.user_output.p_tof.get_active(item=0))
        self.SetNeutronEnergyFlag(self.user_output.n_E.get_active(item=0))
        self.SetNeutronTimeFlag(self.user_output.n_tof.get_active(item=0))

        self.SetVector(self.user_info.get("vect_p"), self.user_info.get("vect_n"))

        self.SetPhysicalVolumeName(self.user_info.get("attached_to"))
        self.InitializeCpp()

    def prepare_output_for_run(self, output_name, run_index, **kwargs):
        # need to override because create image is different for img of histo
        self._assert_output_exists(output_name)
        if (output_name == "p_E") or (output_name == "n_E"):
            self.user_output[output_name].create_image_of_histograms(
                run_index,
                self.size,
                self.spacing,
                self.energybins + 1,
                origin=self.translation,
                **kwargs,
            )
        if (output_name == "p_tof") or (output_name == "n_tof"):
            self.user_output[output_name].create_image_of_histograms(
                run_index,
                self.size,
                self.spacing,
                self.timebins + 1,
                origin=self.translation,
                **kwargs,
            )

    def BeginOfRunActionMasterThread(self, run_index):
        if self.user_output.p_E.get_active(item=0):
            self.prepare_output_for_run("p_E", run_index)
            self.push_to_cpp_image("p_E", run_index, self.cpp_E_proton_image)
        if self.user_output.p_tof.get_active(item=0):
            self.prepare_output_for_run("p_tof", run_index)
            self.push_to_cpp_image("p_tof", run_index, self.cpp_tof_proton_image)
        if self.user_output.n_E.get_active(item=0):
            self.prepare_output_for_run("n_E", run_index)
            self.push_to_cpp_image("n_E", run_index, self.cpp_E_neutron_image)
        if self.user_output.n_tof.get_active(item=0):
            self.prepare_output_for_run("n_tof", run_index)
            self.push_to_cpp_image("n_tof", run_index, self.cpp_tof_neutron_image)
        g4.GateVoxelizedPromptGammaTLEActor.BeginOfRunActionMasterThread(
            self, run_index
        )

    def EndOfRunActionMasterThread(self, run_index):
        if self.user_output.p_E.get_active(item=0):
            self.fetch_from_cpp_image("p_E", run_index, self.cpp_E_proton_image)
            self._update_output_coordinate_system("p_E", run_index)
        if self.user_output.p_tof.get_active(item=0):
            self.fetch_from_cpp_image("p_tof", run_index, self.cpp_tof_proton_image)
            self._update_output_coordinate_system("p_tof", run_index)
        if self.user_output.n_E.get_active(item=0):
            self.fetch_from_cpp_image("n_E", run_index, self.cpp_E_neutron_image)
            self._update_output_coordinate_system("n_E", run_index)
        if self.user_output.n_tof.get_active(item=0):
            self.fetch_from_cpp_image("n_tof", run_index, self.cpp_tof_neutron_image)
            self._update_output_coordinate_system("n_tof", run_index)
        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateVoxelizedPromptGammaTLEActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


class VoxelizedPromptGammaAnalogActor(
    VoxelDepositActor, g4.GateVoxelizedPromptGammaAnalogActor
):
    """
    FIXME doc todo
    """

    user_info_defaults = {
        "timebins": (
            200,
            {
                "doc": "Number of bins in the histogram for time",
            },
        ),
        "timerange": (
            5 * g4_units.ns,
            {
                "doc": "Range of the histogram in ns",
            },
        ),
        "energybins": (
            250,
            {
                "doc": "Number of bins in the histogram for energy",
            },
        ),
        "energyrange": (
            200 * g4_units.MeV,
            {
                "doc": "Range of the histogram in MeV",
            },
        ),
    }

    user_output_config = {
        "p_E": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "prot_E": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": True,
                },
            },
        },
        "p_tof": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "prot_tof": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": False,
                },
            },
        },
        "n_E": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "neutr_E": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": False,
                },
            },
        },
        "n_tof": {
            "actor_output_class": ActorOutputSingleImageOfHistogram,
            "interfaces": {
                "neutr_tof": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": False,
                },
            },
        },
    }

    def __init__(self, *args, **kwargs):

        VoxelDepositActor.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):

        g4.GateVoxelizedPromptGammaAnalogActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "BeginOfEventAction",
                "BeginOfRunAction",
                "SteppingAction",
                "EndOfRunAction",
                "EndOfRunActionMasterThread",
            }
        )

    def initialize(self, *args):

        self.check_user_input()
        VoxelDepositActor.initialize(self)
        if not (self.user_output.p_E.get_active(item=0)):
            self.user_output.p_E.set_write_to_disk(False, item=0)
        if not (self.user_output.p_tof.get_active(item=0)):
            self.user_output.p_tof.set_write_to_disk(False, item=0)
        if not (self.user_output.n_E.get_active(item=0)):
            self.user_output.n_E.set_write_to_disk(False, item=0)
        if not (self.user_output.n_tof.get_active(item=0)):
            self.user_output.n_tof.set_write_to_disk(False, item=0)

        self.InitializeUserInfo(self.user_info)

        self.SetProtonEnergyFlag(self.user_output.p_E.get_active(item=0))
        self.SetProtonTimeFlag(self.user_output.p_tof.get_active(item=0))
        self.SetNeutronEnergyFlag(self.user_output.n_E.get_active(item=0))
        self.SetNeutronTimeFlag(self.user_output.n_tof.get_active(item=0))

        self.SetPhysicalVolumeName(self.user_info.get("attached_to"))
        self.InitializeCpp()

    def prepare_output_for_run(self, output_name, run_index, **kwargs):
        # need to override because create image is different for img of histo
        self._assert_output_exists(output_name)
        if (output_name == "p_E") or (output_name == "n_E"):
            self.user_output[output_name].create_image_of_histograms(
                run_index,
                self.size,
                self.spacing,
                self.energybins + 1,
                origin=self.translation,
                **kwargs,
            )
        if (output_name == "p_tof") or (output_name == "n_tof"):
            self.user_output[output_name].create_image_of_histograms(
                run_index,
                self.size,
                self.spacing,
                self.timebins + 1,
                origin=self.translation,
                **kwargs,
            )

    def BeginOfRunActionMasterThread(self, run_index):

        if self.user_output.p_E.get_active(item=0):
            self.prepare_output_for_run("p_E", run_index)
            self.push_to_cpp_image("p_E", run_index, self.cpp_E_proton_image)
        if self.user_output.p_tof.get_active(item=0):
            self.prepare_output_for_run("p_tof", run_index)
            self.push_to_cpp_image("p_tof", run_index, self.cpp_tof_proton_image)
        if self.user_output.n_E.get_active(item=0):
            self.prepare_output_for_run("n_E", run_index)
            self.push_to_cpp_image("n_E", run_index, self.cpp_E_neutron_image)
        if self.user_output.n_tof.get_active(item=0):
            self.prepare_output_for_run("n_tof", run_index)
            self.push_to_cpp_image("n_tof", run_index, self.cpp_tof_neutron_image)
        g4.GateVoxelizedPromptGammaAnalogActor.BeginOfRunActionMasterThread(
            self, run_index
        )

    def EndOfRunActionMasterThread(self, run_index):
        if self.user_output.p_E.get_active(item=0):
            self.fetch_from_cpp_image("p_E", run_index, self.cpp_E_proton_image)
            self._update_output_coordinate_system("p_E", run_index)
        if self.user_output.p_tof.get_active(item=0):
            self.fetch_from_cpp_image("p_tof", run_index, self.cpp_tof_proton_image)
            self._update_output_coordinate_system("p_tof", run_index)
        if self.user_output.n_E.get_active(item=0):
            self.fetch_from_cpp_image("n_E", run_index, self.cpp_E_neutron_image)
            self._update_output_coordinate_system("n_E", run_index)
        if self.user_output.n_tof.get_active(item=0):
            self.fetch_from_cpp_image("n_tof", run_index, self.cpp_tof_neutron_image)
            self._update_output_coordinate_system("n_tof", run_index)
        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateVoxelizedPromptGammaAnalogActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


process_cls(VoxelizedPromptGammaTLEActor)
process_cls(VoxelizedPromptGammaAnalogActor)
