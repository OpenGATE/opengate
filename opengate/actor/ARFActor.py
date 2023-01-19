import opengate_core as g4
import opengate as gate
import sys
from box import Box
import numpy as np
import itk


class ARFActor(g4.GateARFActor, gate.ActorBase):
    """
    The ARF Actor is attached to a volume.
    Every time a particle enter, it considers the energy and the direction of the particle.
    It runs the neural network model to provide the probability of detection in all energy windows.

    Output is an (FIXME itk ?numpy ?) image that can be retrieved with self.output_image
    """

    type_name = "ARFActor"

    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        # required user info, default values
        # user_info.arf_detector = None
        user_info.batch_size = 2e5
        user_info.pth_filename = None
        user_info.image_size = [128, 128]
        mm = gate.g4_units("mm")
        user_info.image_spacing = [4.41806 * mm, 4.41806 * mm]
        user_info.distance_to_crystal = 75 * mm
        user_info.verbose_batch = False
        user_info.output = ""

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateARFActor.__init__(self, user_info.__dict__)
        # import module
        self.garf = gate.import_garf()
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

    def __str__(self):
        u = self.user_info
        s = f'ARFActor "{u.name}"'
        return s

    def __getstate__(self):
        # needed to not pickle. Need to reset some attributes
        gate.ActorBase.__getstate__(self)
        self.garf = None
        self.nn = None
        self.output_image = None
        return self.__dict__

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)
        # self.user_info.arf_detector.initialize(self)
        self.ActorInitialize()
        self.SetARFFunction(self.apply)
        self.user_info.output_image = None

        # load the pth file
        self.nn, self.model = self.garf.load_nn(
            self.pth_filename, gpu="auto", verbose=False
        )
        p = self.param
        p.gpu_batch_size = int(float(self.user_info.batch_size))

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

    def apply(self, actor):
        # get values from cpp side
        energy = np.array(actor.fEnergy)
        px = np.array(actor.fPositionX)
        py = np.array(actor.fPositionY)
        dx = np.array(actor.fDirectionX)
        dy = np.array(actor.fDirectionY)

        # convert direction in angles # FIXME or CPP side ?
        degree = gate.g4_units("degree")
        theta = np.arccos(dy) / degree
        phi = np.arccos(dx) / degree

        # update
        self.batch_nb += 1
        self.detected_particles += energy.shape[0]

        # build the data
        x = np.column_stack((px, py, theta, phi, energy))

        # apply the neural network
        if self.user_info.verbose_batch:
            print(f"Apply ARF neural network to {energy.shape[0]} samples")
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
            run_id = (
                self.simulation_engine_wr().g4_RunManager.GetCurrentRun().GetRunID()
            )
            s = p.nb_ene * run_id
            self.output_image[s : s + p.nb_ene] = (
                self.output_image[s : s + p.nb_ene] + temp
            )

    def EndSimulationAction(self):
        g4.GateARFActor.EndSimulationAction(self)
        # process the remaining elements in the batch
        self.apply(self)
        # convert to itk image
        self.output_image = itk.image_from_array(self.output_image)
        # set spacing and origin like HitsProjectionActor
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
            itk.imwrite(
                self.output_image, gate.check_filename_type(self.user_info.output)
            )
