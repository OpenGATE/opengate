import sys
from box import Box
import numpy as np
import itk
import threading
import opengate_core as g4
from ..utility import g4_units, ensure_filename_is_str
from ..exception import fatal
from .digitizers import DigitizerHitsCollectionActor
from .base import ActorBase
from ..image import write_itk_image


def import_garf():
    # Try to import torch
    try:
        import torch
    except:
        fatal(
            f'The module "torch" is needed, see https://pytorch.org/get-started/locally/ to install it'
        )

    # Try to import garf_phsp
    try:
        import garf
    except:
        fatal("The module \"garf\" is needed. Use ' pip install garf'")

    # Check minimal version of garf
    import pkg_resources
    from packaging import version

    garf_version = pkg_resources.get_distribution("garf").version
    garf_minimal_version = "2.5"
    if version.parse(garf_version) < version.parse(garf_minimal_version):
        fatal(
            "The minimal version of garf is not correct. You should install at least the version "
            + garf_minimal_version
            + ". Your version is "
            + garf_version
        )
    return garf


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


class ARFTrainingDatasetActor(g4.GateARFTrainingDatasetActor, ActorBase):
    """
    The ARFTrainingDatasetActor build a root file with energy, angles, positions and energy windows
    of a spect detector. To be used by garf_train to train a ARF neural network.

    Note: Must inherit from ActorBase not from HitsCollectionActor, even if the
    cpp part inherit from HitsCollectionActor
    """

    type_name = "ARFTrainingDatasetActor"

    @staticmethod
    def set_default_user_info(user_info):
        DigitizerHitsCollectionActor.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "arf_training.root"
        user_info.debug = False
        user_info.energy_windows_actor = None
        user_info.russian_roulette = 1

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateARFTrainingDatasetActor.__init__(self, user_info.__dict__)

    def initialize(self, simulation_engine_wr=None):
        ActorBase.initialize(self, simulation_engine_wr)
        # check the energy_windows_actor
        ewa_name = self.user_info.energy_windows_actor
        ewa = self.simulation.get_actor_user_info(ewa_name)
        if ewa.type_name != "DigitizerEnergyWindowsActor":
            fatal(
                f"In the actor '{self.user_info.name}', the parameter 'energy_windows_actor' is {ewa.type_name}"
                f" while it must be a DigitizerEnergyWindowsActor"
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

    def __str__(self):
        s = f"ARFTrainingDatasetActor {self.user_info.name}"
        return s


class ARFActor(g4.GateARFActor, ActorBase):
    """
    The ARF Actor is attached to a volume.
    Every time a particle enter, it considers the energy and the direction of the particle.
    It runs the neural network model to provide the probability of detection in all energy windows.

    Output is an ITK image that can be retrieved with self.output_image
    """

    type_name = "ARFActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        # required user info, default values
        # user_info.arf_detector = None
        user_info.batch_size = 2e5
        user_info.pth_filename = None
        user_info.image_size = [128, 128]
        mm = g4_units.mm
        user_info.image_spacing = [4.41806 * mm, 4.41806 * mm]
        user_info.distance_to_crystal = 75 * mm
        user_info.verbose_batch = False
        user_info.output = ""
        user_info.enable_hit_slice = False
        user_info.flip_plane = False
        # Can be cpu / auto / gpu
        user_info.gpu_mode = "auto"

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateARFActor.__init__(self, user_info.__dict__)
        # import module
        self.debug_nb_hits_before = None
        self.debug_nb_hits = 0
        self.garf = import_garf()
        if self.garf is None:
            print("Cannot run GANSource")
            sys.exit()

        # prepare output
        self.user_info.output_image = None
        self.g4_actor = None
        self.pth_filename = user_info.pth_filename
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
        self.nb_ene = None

    def __str__(self):
        u = self.user_info
        s = f'ARFActor "{u.name}"'
        return s

    def __getstate__(self):
        # needed to not pickle objects that cannot be pickled (g4, cuda, lock, etc).
        ActorBase.__getstate__(self)
        self.garf = None
        self.nn = None
        self.output_image = None
        self.lock = None
        self.model = None
        return self.__dict__

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)
        self.ActorInitialize()
        self.SetARFFunction(self.apply)
        self.user_info.output_image = None
        self.debug_nb_hits_before = 0
        self.debug_nb_hits = 0

        # load the pth file
        self.nn, self.model = self.garf.load_nn(
            self.pth_filename, verbose=False, gpu_mode=self.user_info.gpu_mode
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
        output_size = [
            self.nb_ene * nb_runs,
            self.output_image[1],
            self.output_image[2],
        ]
        self.output_image = np.zeros(output_size, dtype=np.float64)

        # which device for GARF : cpu cuda mps ?
        if self.user_info.gpu_mode not in ("cpu", "gpu", "auto"):
            fatal(
                f"the gpu_mode must be 'cpu' or 'auto' or 'gpu', while is is '{self.user_info.gpu_mode}'"
            )
        current_gpu_mode, current_gpu_device = self.garf.helpers.get_gpu_device(
            self.user_info.gpu_mode
        )
        self.model_data["current_gpu_device"] = current_gpu_device
        self.model_data["current_gpu_mode"] = current_gpu_mode
        self.model.to(current_gpu_device)

    def apply(self, actor):
        # we need a lock when the ARF is applied
        with self.lock:
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
        if self.user_info.verbose_batch:
            print(
                f"Apply ARF to {energy.shape[0]} hits (device = {self.model_data['current_gpu_mode']})"
            )

        # from projected points to image counts
        u, v, w_pred = self.garf.arf_from_points_to_image_counts(
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
            img = self.output_image[s : s + self.nb_ene]
            self.garf.image_from_coordinates_add_numpy(img, u, v, w_pred)
            self.debug_nb_hits += u.shape[0]

    def EndSimulationAction(self):
        g4.GateARFActor.EndSimulationAction(self)
        # process the remaining elements in the batch
        self.apply(self)

        # Should we keep the first slice (with all hits) ?
        nb_slice = self.nb_ene
        if not self.user_info.enable_hit_slice:
            self.output_image = self.output_image[1:, :, :]
            # self.param.image_size[0] = self.param.image_size[0] - 1
            nb_slice = nb_slice - 1

        # convert to itk image
        self.output_image = itk.image_from_array(self.output_image)

        # set spacing and origin like DigitizerProjectionActor
        spacing = self.user_info.image_spacing
        spacing = np.array([spacing[0], spacing[1], 1])
        size = np.array([0, 0, 0])
        size[0] = self.image_plane_size_pixel[0]
        size[1] = self.image_plane_size_pixel[1]
        size[2] = nb_slice
        origin = -size / 2.0 * spacing + spacing / 2.0
        origin[2] = 0
        self.output_image.SetSpacing(spacing)
        self.output_image.SetOrigin(origin)

        # convert double to float
        InputImageType = itk.Image[itk.D, 3]
        OutputImageType = itk.Image[itk.F, 3]
        castImageFilter = itk.CastImageFilter[InputImageType, OutputImageType].New()
        castImageFilter.SetInput(self.output_image)
        castImageFilter.Update()
        self.output_image = castImageFilter.GetOutput()

        # write ?
        if self.user_info.output:
            write_itk_image(
                self.output_image, ensure_filename_is_str(self.user_info.output)
            )

        # debug
        # print(f"{self.debug_nb_hits_before=}")
        # print(f"{self.debug_nb_hits=}")
