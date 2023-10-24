import sys
from box import Box
import numpy as np
import itk
import threading
import opengate_core as g4
from ..utility import g4_units, check_filename_type
from ..exception import fatal
from .digitizers import DigitizerHitsCollectionActor
from .base import ActorBase


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
    garf_minimal_version = "2.4"
    if version.parse(garf_version) < version.parse(garf_minimal_version):
        fatal(
            "The minimal version of garf is not correct. You should install at least the version "
            + garf_minimal_version
            + ". Your version is "
            + garf_version
        )
    return garf


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

    def __del__(self):
        pass

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
        # Can be cpu / auto / gpu
        user_info.gpu_mode = "auto"

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateARFActor.__init__(self, user_info.__dict__)
        # import module
        self.garf = import_garf()
        if self.garf is None:
            print("Cannot run GANSource")
            sys.exit()
        # create the default detector
        # self.user_info.arf_detector = gate.ARFDetector(self.user_info)
        # prepare output
        self.user_info.output_image = None
        self.g4_actor = None
        self.pth_filename = user_info.pth_filename
        self.param = Box()
        self.nn = None
        self.model = None
        self.model_data = None
        self.batch_nb = 0
        self.detected_particles = 0
        # need a lock when the ARF is applied
        self.lock = threading.Lock()

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
        # self.user_info.arf_detector.initialize(self)
        self.ActorInitialize()
        self.SetARFFunction(self.apply)
        self.user_info.output_image = None

        # load the pth file
        self.nn, self.model = self.garf.load_nn(self.pth_filename, verbose=False)
        p = self.param
        p.batch_size = int(float(self.user_info.batch_size))

        # size and spacing (2D)
        p.image_size = self.user_info.image_size
        p.image_spacing = self.user_info.image_spacing
        p.distance_to_crystal = self.user_info.distance_to_crystal
        self.model_data = self.nn["model_data"]

        # output image: nb of energy windows times nb of runs (for rotation)
        p.nb_ene = self.model_data["n_ene_win"]
        p.nb_runs = len(self.simulation.run_timing_intervals)
        # size and spacing in 3D
        p.image_size = [p.nb_ene, p.image_size[0], p.image_size[1]]
        p.image_spacing = [p.image_spacing[0], p.image_spacing[1], 1]
        # create output image as np array
        p.output_size = [p.nb_ene * p.nb_runs, p.image_size[1], p.image_size[2]]
        self.output_image = np.zeros(p.output_size, dtype=np.float64)
        # compute offset
        p.psize = [
            p.image_size[1] * p.image_spacing[0],
            p.image_size[2] * p.image_spacing[1],
        ]
        p.hsize = np.divide(p.psize, 2.0)
        p.offset = [p.image_spacing[0] / 2.0, p.image_spacing[1] / 2.0]

        # which device for GARF : cpu cuda mps ?
        # we recommend CPU only
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
            self.apply_with_lock(actor)

    def apply_with_lock(self, actor):
        # get values from cpp side
        energy = np.array(actor.GetEnergy())
        px = np.array(actor.GetPositionX())
        py = np.array(actor.GetPositionY())
        dx = np.array(actor.GetDirectionX())
        dy = np.array(actor.GetDirectionY())

        # do nothing if no hits
        if energy.size == 0:
            return

        # convert direction in angles
        # FIXME would it be faster on CPP side ?
        degree = g4_units.degree
        theta = np.arccos(dy) / degree
        phi = np.arccos(dx) / degree

        # update
        self.batch_nb += 1
        self.detected_particles += energy.shape[0]

        # build the data
        x = np.column_stack((px, py, theta, phi, energy))

        # apply the neural network
        if self.user_info.verbose_batch:
            print(
                f"Apply ARF to {energy.shape[0]} hits (device = {self.model_data['current_gpu_mode']})"
            )
        ax = x[:, 2:5]  # two angles and energy
        w = self.garf.nn_predict(self.model, self.nn["model_data"], ax)

        # positions
        p = self.param
        angles = x[:, 2:4]
        t = self.garf.compute_angle_offset(angles, p.distance_to_crystal)
        cx = x[:, 0:2]
        cx = cx + t
        coord = (cx + p.hsize - p.offset) / p.image_spacing[0:2]
        coord = np.around(coord).astype(int)
        v = coord[:, 0]
        u = coord[:, 1]
        u, v, w_pred = self.garf.remove_out_of_image_boundaries(u, v, w, p.image_size)

        # do nothing if there is no hit in the image
        if u.shape[0] != 0:
            temp = np.zeros(p.image_size, dtype=np.float64)
            temp = self.garf.image_from_coordinates(temp, u, v, w_pred)
            # add to previous, at the correct slice location
            # the slice is : current_ene_window + run_id * nb_ene_windows
            run_id = actor.GetCurrentRunId()
            # self.simulation_engine_wr().g4_RunManager.GetCurrentRun().GetRunID()
            s = p.nb_ene * run_id
            self.output_image[s : s + p.nb_ene] = (
                self.output_image[s : s + p.nb_ene] + temp
            )

    def EndSimulationAction(self):
        g4.GateARFActor.EndSimulationAction(self)
        # process the remaining elements in the batch
        self.apply(self)

        # Should we keep the first slice (with all hits) ?
        if not self.user_info.enable_hit_slice:
            self.output_image = self.output_image[1:, :, :]
            self.param.image_size[1] = self.param.image_size[1] - 1

        # convert to itk image
        self.output_image = itk.image_from_array(self.output_image)

        # set spacing and origin like DigitizerProjectionActor
        spacing = self.user_info.image_spacing
        spacing = np.array([spacing[0], spacing[1], 1])
        size = np.array(self.param.image_size)
        size[0] = self.param.image_size[2]
        size[2] = self.param.image_size[0]
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
            itk.imwrite(self.output_image, check_filename_type(self.user_info.output))
