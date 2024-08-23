from box import Box
import numpy as np
import itk
import threading
import opengate_core as g4
from ..utility import g4_units
from ..exception import fatal
from .base import ActorBase

from .digitizers import DigitizerEnergyWindowsActor, DigitizerBase
from .actoroutput import ActorOutputRoot, ActorOutputSingleImage


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


class ARFTrainingDatasetActor(DigitizerBase, g4.GateARFTrainingDatasetActor):
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
        "russian_roulette": (1, {"doc": "Russian roulette factor. "}),
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        g4.GateARFTrainingDatasetActor.__init__(self, self.user_info)
        self._add_user_output_root(
            output_filename="arf_training.root",
        )

    def initialize(self):
        ActorBase.initialize(self)

        self.check_energy_window_actor()

        # initialize C++ side
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def check_energy_window_actor(self):
        # check the energy_windows_actor
        if not self.energy_windows_actor in self.simulation.actor_manager.actors:
            fatal(
                f"The actor '{self.name}' has the user input energy_windows_actor={self.energy_windows_actor}, "
                f"but no actor with this name was found in the simulation."
            )
        ewa = self.simulation.actor_manager.get_actor(self.energy_windows_actor)
        if not isinstance(ewa, DigitizerEnergyWindowsActor):
            fatal(
                f"The actor '{self.name}' has the user input energy_windows_actor={self.energy_windows_actor}, "
                f"but {ewa.name} is not the correct type of actor. "
                f"It should be a DigitizerEnergyWindowsActor, while it is a {type(ewa).__name}. "
            )


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
        g4.GateARFActor.__init__(self, self.user_info)  # call the C++ constructor
        # import module
        self.debug_nb_hits_before = None
        self.debug_nb_hits = 0
        self.garf = import_garf()
        if self.garf is None:
            fatal("Cannot run GANSource")
        # create the default detector
        # self.user_info.arf_detector = gate.ARFDetector(self.user_info)
        # prepare output
        self.param = Box()
        self.nn = None
        self.model = None
        self.model_data = None
        self.batch_nb = 0
        self.detected_particles = 0
        # need a lock when the ARF is applied
        self.lock = threading.Lock()
        self.output_array = None

        self._add_user_output(
            ActorOutputSingleImage,
            "arf_projection",
            output_filename="arf_projection.mhd",
            keep_in_memory=True,
        )

    def __getstate__(self):
        # needed to not pickle objects that cannot be pickled (g4, cuda, lock, etc).
        return_dict = super().__getstate__()
        return_dict["garf"] = None
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

        self.output_array = np.zeros(self.param.output_size, dtype=np.float64)

        # initialize C++ side
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()
        self.SetARFFunction(self.apply)

    def initialize_model(self):
        # load the pth file
        self.nn, self.model = self.garf.load_nn(self.pth_filename, verbose=False)
        self.model_data = self.nn["model_data"]

    def initialize_device(self):
        # which device for GARF : cpu cuda mps ?
        # we recommend CPU only
        current_gpu_mode, current_gpu_device = self.garf.helpers.get_gpu_device(
            self.gpu_mode
        )
        self.model_data["current_gpu_device"] = current_gpu_device
        self.model_data["current_gpu_mode"] = current_gpu_mode
        self.model.to(current_gpu_device)

    def initialize_params(self):
        self.param.batch_size = int(float(self.batch_size))
        self.param.image_size = self.image_size
        self.param.image_spacing = self.image_spacing
        self.param.distance_to_crystal = self.distance_to_crystal

        # output image: nb of energy windows times nb of runs (for rotation)
        self.param.nb_ene = self.model_data["n_ene_win"]
        self.param.nb_runs = len(self.simulation.run_timing_intervals)
        # size and spacing in 3D
        self.param.image_size = [
            self.param.nb_ene,
            self.param.image_size[0],
            self.param.image_size[1],
        ]
        self.param.image_spacing = [
            self.param.image_spacing[0],
            self.param.image_spacing[1],
            1,
        ]
        # create output image as np array
        self.param.output_size = [
            self.param.nb_ene * self.param.nb_runs,
            self.param.image_size[1],
            self.param.image_size[2],
        ]
        # compute offset
        self.param.psize = [
            self.param.image_size[1] * self.param.image_spacing[0],
            self.param.image_size[2] * self.param.image_spacing[1],
        ]
        self.param.hsize = np.divide(self.param.psize, 2.0)
        self.param.offset = [
            self.param.image_spacing[0] / 2.0,
            self.param.image_spacing[1] / 2.0,
        ]

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
        self.debug_nb_hits_before += len(x)

        # apply the neural network
        if self.verbose_batch:
            print(
                f"Apply ARF to {energy.shape[0]} hits (device = {self.model_data['current_gpu_mode']})"
            )

        ax = x[:, 2:5]  # two angles and energy # FIXME index ?
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
        u, v, w_pred = self.garf.remove_out_of_image_boundaries2(
            u, v, w, self.image_size
        )

        # do nothing if there is no hit in the image
        if u.shape[0] != 0:
            run_id = actor.GetCurrentRunId()
            s = p.nb_ene * run_id
            img = self.output_array[s : s + p.nb_ene]
            self.garf.image_from_coordinates_add(img, u, v, w_pred)
            self.debug_nb_hits += u.shape[0]

    def EndOfRunActionMasterThread(self, run_index):
        # Should we keep the first slice (with all hits) ?
        if not self.enable_hit_slice:
            self.output_array = self.output_array[1:, :, :]
            self.param.image_size[0] = self.param.image_size[0] - 1

        # convert to itk image
        # FIXME: this should probably go into EndOfRunAction
        output_image = itk.image_from_array(self.output_array)

        # set spacing and origin like DigitizerProjectionActor
        spacing = self.image_spacing
        spacing = np.array([spacing[0], spacing[1], 1])
        size = np.array(self.param.image_size)
        size[0] = self.param.image_size[2]
        size[2] = self.param.image_size[0]
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

        self.store_output_data("projection", run_index, output_image)

        return 0

    def EndSimulationAction(self):
        g4.GateARFActor.EndSimulationAction(self)
        # process the remaining elements in the batch
        self.apply(self)
        self.user_output["projection"].write_data_if_requested()
