import gam_gate as gam
import sys
import numpy as np
from box import Box


class ARFDetector:

    def __init__(self, user_info):
        self.data_img = None
        self.user_info = user_info
        self.garf = gam.import_garf()
        self.g4_actor = None  # FIXME not needed if set with 'apply'
        self.pth_filename = None
        self.param = Box()
        self.nn = None
        self.model = None
        self.model_data = None
        if self.garf is None:
            print("Cannot run GANSource")
            sys.exit()
        print('garf import ok')

    def initialize(self, actor):
        print('ARFDetector initialize')
        self.g4_actor = actor  # FIXME not needed if set with 'apply'

        # load the pth file
        mm = gam.g4_units('mm')
        print('Loading', self.pth_filename)
        self.nn, self.model = self.garf.load_nn(self.pth_filename, gpu='auto', verbose=True)
        p = self.param
        p.gpu_batch_size = int(float(self.user_info.batch_size))
        p.size = 128
        p.spacing = 4.41806
        p.length = 99 * mm  ## FIXME depends on colli ?
        p.N_scale = 1
        p.N_dataset = 1
        self.model_data = self.nn['model_data']
        print(self.param)
        # print(self.nn)

        print('Check RR = ', self.model_data['RR'])

        # output image
        p.nb_ene = self.model_data['n_ene_win']
        p.size = [p.nb_ene, p.size, p.size]
        p.spacing = [p.spacing, p.spacing, 1]
        print(p.size)
        print(p.spacing)
        self.data_img = np.zeros(p.size, dtype=np.float64)
        p.psize = [p.size[1] * p.spacing[0], p.size[2] * p.spacing[1]]
        print('psize', p.psize)
        p.hsize = np.divide(p.psize, 2.0)
        print('hsize', p.hsize)
        p.offset = [p.spacing[0] / 2.0, p.spacing[1] / 2.0]
        print(p)

    def apply(self, actor):
        print('RFDetector apply')

        # get values from cpp side
        energy = np.array(actor.fEnergy)
        px = np.array(actor.fPositionX)
        py = np.array(actor.fPositionY)
        dx = np.array(actor.fDirectionX)
        dy = np.array(actor.fDirectionY)

        # convert direction in angles # FIXME or CPP side ?
        degree = gam.g4_units('degree')
        theta = np.arccos(dy) / degree
        phi = np.arccos(dx) / degree

        # build the data
        x = np.column_stack((px, py, theta, phi, energy))  # or vstack ?
        print('x shape', x.shape)

        # apply the neural network
        ax = x[:, 2:5]  # two angles and energy
        w = self.garf.nn_predict(self.model, self.nn['model_data'], ax)

        # debug
        nb_ene = len(w[0])
        print('nb ene', nb_ene)

        # positions
        p = self.param
        angles = x[:, 2:4]
        print('compute_angle_offset')
        t = self.garf.compute_angle_offset(angles, p.length)
        cx = x[:, 0:2]
        cx = cx + t
        coord = (cx + p.hsize - p.offset) / p.spacing[0:2]
        coord = np.around(coord).astype(int)
        v = coord[:, 0]
        u = coord[:, 1]
        print('remove_out_of_image_boundaries')
        u, v, w_pred = self.garf.remove_out_of_image_boundaries(u, v, w, p.size)
        print('image_from_coordinates')
        temp = np.zeros(p.size, dtype=np.float64)
        temp = self.garf.image_from_coordinates(temp, u, v, w_pred)

        # add to previous
        print('data img', self.data_img.shape, np.min(self.data_img), np.max(self.data_img))
        print('temp', temp.shape, np.min(temp), np.max(temp))
        self.data_img = self.data_img + temp
        print('data img', self.data_img.shape, np.min(self.data_img), np.max(self.data_img))
