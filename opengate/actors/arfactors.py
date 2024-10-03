from box import Box
import numpy as np
import itk
import threading

import opengate_core as g4
from ..utility import g4_units, LazyModuleLoader
from ..exception import fatal
from .base import ActorBase
from .digitizers import (
    DigitizerEnergyWindowsActor,
)
from .actoroutput import ActorOutputSingleImage, ActorOutputRoot
from ..base import process_cls

garf = LazyModuleLoader("garf")


def check_channel_overlap(ch1, ch2):
    ch1 = Box(ch1)
    ch2 = Box(ch2)
    if ch2.min < ch1.min < ch2.max:
        return True
    if ch2.min < ch1.max < ch2.max:
        return True
    if ch1.min < ch2.min < ch1.max:
        return True
    if ch1.min < ch2.max < ch1.max:
        return True
    return False


class ARFTrainingDatasetActor(ActorBase, g4.GateARFTrainingDatasetActor):
    """
    The ARFTrainingDatasetActor build a root file with energy, angles, positions and energy windows
    of a spect detector. To be used by garf_train to train a ARF neural network.

    Note: Must inherit from ActorBase not from HitsCollectionActor, even if the
    cpp part inherit from HitsCollectionActor
    """

    user_info_defaults = {
        "attributes": (
            [],
            {
                "doc": "FIXME",
            },
        ),
        "debug": (False, {"doc": "FIXME"}),
        "energy_windows_actor": (
            None,
            {
                "doc": "",
            },
        ),
        # duplicated because cpp part inherit from HitsCollectionActor
        "clear_every": (
            1e5,
            {
                "doc": "FIXME",
            },
        ),
        # duplicated because cpp part inherit from HitsCollectionActor
        "keep_zero_edep": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "russian_roulette": (1, {"doc": "Russian roulette factor. "}),
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self._add_user_output(ActorOutputRoot, "root_output")
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateARFTrainingDatasetActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "SteppingAction",
                # "BeginOfRunActionMasterThread",
                # "EndOfRunActionMasterThread",
                "BeginOfEventAction",
                "EndOfEventAction",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.check_energy_window_actor()
        # initialize C++ side
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateARFTrainingDatasetActor.StartSimulationAction(self)

    def check_energy_window_actor(self):
        # check the energy_windows_actor
        if not self.energy_windows_actor in self.simulation.actor_manager.actors:
            fatal(
                f"The actor '{self.name}' has the user input energy_windows_actor={self.energy_windows_actor}, "
                f"but no actor with this name was found in the simulation."
            )
        ewa = self.simulation.get_actor(self.energy_windows_actor)
        if not isinstance(ewa, DigitizerEnergyWindowsActor):
            fatal(
                f"The actor '{self.name}' has the user input energy_windows_actor={self.energy_windows_actor}, "
                f"but {ewa.name} is not the correct type of actor. "
                f"It should be a DigitizerEnergyWindowsActor, while it is a {type(ewa).__name}. "
            )
        # check overlap in channels
        channels = ewa.channels
        for i, ch1 in enumerate(channels):
            for j, ch2 in enumerate(channels[i + 1 :]):
                is_overlap = check_channel_overlap(ch1, ch2)
                if is_overlap:
                    fatal(
                        f'In the actor "{self.user_info.name}", the energy channels '
                        f"{i} and {i + 1 + j} overlap. This is not possible for ARF. \n"
                        f"{ch1} {ch2}"
                    )

    def EndSimulationAction(self):
        g4.GateARFTrainingDatasetActor.EndSimulationAction(self)
        ActorBase.EndSimulationAction(self)


def _setter_hook_image_spacing(self, image_spacing):
    # force float
    return [float(s) for s in image_spacing]


class ARFActor(ActorBase, g4.GateARFActor):
    """
    The ARF Actor is attached to a volume.
    Every time a particle enter, it considers the energy and the direction of the particle.
    It runs the neural network model to provide the probability of detection in all energy windows.

    Output is an ITK image that can be retrieved with self.output_image
    """

    user_info_defaults = {
        "batch_size": (
            2e5,
            {
                "doc": "FIXME",
            },
        ),
        "pth_filename": (
            None,
            {
                "doc": "FIXME",
            },
        ),
        "image_size": (
            [128, 128],
            {
                "doc": "FIXME",
            },
        ),
        "image_spacing": (
            [4.41806 * g4_units.mm, 4.41806 * g4_units.mm],
            {"doc": "FIXME", "setter_hook": _setter_hook_image_spacing},
        ),
        "distance_to_crystal": (
            75 * g4_units.mm,
            {
                "doc": "FIXME",
            },
        ),
        "verbose_batch": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "enable_hit_slice": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "flip_plane": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "gpu_mode": (
            "auto",
            {"doc": "FIXME", "allowed_values": ("cpu", "gpu", "auto")},
        ),
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        # import module
        self.debug_nb_hits_before = None
        self.debug_nb_hits = 0
        # prepare output
        self.nn = None
        self.model = None
        self.model_data = None
        self.batch_nb = 0
        self.detected_particles = 0
        # need a lock when the ARF is applied
        self.lock = threading.Lock()
        # local variables
        self.image_plane_spacing = None
        self.image_plane_size_pixel = None
        self.image_plane_size_mm = None
        self.output_image = None
        self.output_array = None
        self.output_size = None
        self.nb_ene = None

        self._add_user_output(ActorOutputSingleImage, "arf_projection")
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateARFActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "SteppingAction",
                "BeginOfRunActionMasterThread",
                "EndOfRunActionMasterThread",
                "BeginOfRunAction",
                "EndOfRunAction",
            }
        )

    def __getstate__(self):
        # needed to not pickle objects that cannot be pickled (g4, cuda, lock, etc).
        return_dict = super().__getstate__()
        return_dict["nn"] = None
        return_dict["lock"] = None
        return_dict["model"] = None
        return return_dict

    def initialize(self):
        # call the initialize() method from the super class (python-side)
        ActorBase.initialize(self)

        self.debug_nb_hits_before = 0
        self.debug_nb_hits = 0

        self.initialize_model()
        self.initialize_params()
        self.initialize_device()

        self.output_array = np.zeros(self.output_size, dtype=np.float64)

        # initialize C++ side
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()
        self.SetARFFunction(self.apply)

    def initialize_model(self):
        # load the pth file
        self.nn, self.model = garf.load_nn(
            self.pth_filename, verbose=False, gpu_mode=self.gpu_mode
        )

        # size and spacing (2D)
        self.image_plane_spacing = np.array(
            [self.user_info.image_spacing[0], self.user_info.image_spacing[1]]
        )
        self.image_plane_size_pixel = np.array(
            [self.user_info.image_size[0], self.user_info.image_size[1]]
        )
        self.image_plane_size_mm = (
            self.image_plane_size_pixel * self.image_plane_spacing
        )

        # shortcut to model_data
        self.model_data = self.nn["model_data"]

    def initialize_device(self):
        # which device for GARF : cpu cuda mps ?
        # we recommend CPU only
        current_gpu_mode, current_gpu_device = garf.helpers.get_gpu_device(
            self.gpu_mode
        )
        self.model_data["current_gpu_device"] = current_gpu_device
        self.model_data["current_gpu_mode"] = current_gpu_mode
        self.model.to(current_gpu_device)

    def initialize_params(self):
        # output image: nb of energy windows times nb of runs (for rotation)
        self.nb_ene = self.model_data["n_ene_win"]
        nb_runs = len(self.simulation.run_timing_intervals)
        # size and spacing in 3D
        self.output_image = np.array(
            [
                self.nb_ene,
                self.image_plane_size_pixel[0],
                self.image_plane_size_pixel[1],
            ]
        )
        self.output_size = [
            self.nb_ene * nb_runs,
            self.output_image[1],
            self.output_image[2],
        ]
        self.output_image = np.zeros(self.output_size, dtype=np.float64)

    def apply(self, actor):
        # we need a lock when the ARF is applied
        if self.simulation.use_multithread:
            with self.lock:
                self.arf_build_image_from_projected_points(actor)
        else:
            self.arf_build_image_from_projected_points(actor)

    def arf_build_image_from_projected_points(self, actor):

        # get values from cpp side
        energy = np.array(actor.GetEnergy())
        pos_x = np.array(actor.GetPositionX())
        pos_y = np.array(actor.GetPositionY())
        dir_x = np.array(actor.GetDirectionX())
        dir_y = np.array(actor.GetDirectionY())

        # do nothing if no hits
        if energy.size == 0:
            return

        # convert direction in angles
        degree = g4_units.degree
        theta = np.arccos(dir_y) / degree
        phi = np.arccos(dir_x) / degree

        # update
        self.batch_nb += 1
        self.detected_particles += energy.shape[0]

        # build the data
        px = np.column_stack((pos_x, pos_y, theta, phi, energy))
        self.debug_nb_hits_before += len(px)

        # verbose current batch
        if self.verbose_batch:
            print(
                f"Apply ARF to {energy.shape[0]} hits (device = {self.model_data['current_gpu_mode']})"
            )

        # from projected points to image counts
        u, v, w_pred = garf.arf_from_points_to_image_counts(
            px,
            self.model,
            self.model_data,
            self.user_info.distance_to_crystal,
            self.image_plane_size_mm,
            self.image_plane_size_pixel,
            self.image_plane_spacing,
        )

        # do nothing if there is no hit in the image
        if u.shape[0] != 0:
            run_id = actor.GetCurrentRunId()
            s = self.nb_ene * run_id
            img = self.output_array[s : s + self.nb_ene]
            garf.image_from_coordinates_add_numpy(img, u, v, w_pred)
            self.debug_nb_hits += u.shape[0]

    def EndOfRunActionMasterThread(self, run_index):
        # Should we keep the first slice (with all hits) ?
        nb_slice = self.nb_ene
        if not self.enable_hit_slice:
            self.output_array = self.output_array[1:, :, :]
            # self.param.image_size[0] = self.param.image_size[0] - 1
            nb_slice = nb_slice - 1

        # convert to itk image
        # FIXME: this should probably go into EndOfRunAction
        output_image = itk.image_from_array(self.output_array)

        # set spacing and origin like DigitizerProjectionActor
        spacing = self.image_spacing
        spacing = np.array([spacing[0], spacing[1], 1])
        size = np.array([0, 0, 0])
        size[0] = self.image_plane_size_pixel[0]
        size[1] = self.image_plane_size_pixel[1]
        size[2] = nb_slice
        origin = -size / 2.0 * spacing + spacing / 2.0
        origin[2] = 0
        output_image.SetSpacing(spacing)
        output_image.SetOrigin(origin)

        # convert double to float
        InputImageType = itk.Image[itk.D, 3]
        OutputImageType = itk.Image[itk.F, 3]
        castImageFilter = itk.CastImageFilter[InputImageType, OutputImageType].New()
        castImageFilter.SetInput(output_image)
        castImageFilter.Update()
        output_image = castImageFilter.GetOutput()
        self.user_output["arf_projection"].store_data("merged", output_image)
        # ensure why return 0 ?
        return 0

    def EndSimulationAction(self):
        g4.GateARFActor.EndSimulationAction(self)
        ActorBase.EndSimulationAction(self)
        # process the remaining elements in the batch
        # self.apply()
        # warning('SHOULD call apply here ???')
        self.user_output["arf_projection"].write_data_if_requested(which="merged")


process_cls(ARFActor)
process_cls(ARFTrainingDatasetActor)
