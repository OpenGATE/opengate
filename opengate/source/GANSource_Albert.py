from .GenericSource import *

# from .GANSourceDefaultGenerator import GANSourceDefaultGenerator
# from .GANSource_Albert import GANSource_Albert


#%% Conditional GAN class
import time
import torch
from torch import nn
from torch import Tensor
import pickle
import uproot
import os
import scipy

#%% Functons
#%%% Load
def load_root(filename, nmax=-1):
    """
    Load a PHSP (Phase-Space) file in root format
    Output is numpy structured array
    """

    nmax = int(nmax)
    # Check if file exist
    if not os.path.isfile(filename):
        logger.error("File '" + filename + "' does not exist.")
        exit()

    # Check if this is a root file
    try:
        with uproot.open(filename) as f:
            k = f.keys()
            try:
                psf = f["phase_space"]
            except Exception:
                logger.error(
                    "This root file does not look like a PhaseSpace, keys are: ",
                    f.keys(),
                    ' while expecting "PhaseSpace"',
                )
                exit()

            # Get keys
            names = [k for k in psf.keys()]
            n = psf.num_entries

            # Convert to arrays (this take times)
            if nmax != -1:
                a = psf.arrays(entry_stop=nmax, library="numpy")
            else:
                a = psf.arrays(library="numpy")

            # Concat arrays
            d = np.column_stack([a[k] for k in psf.keys()])
            # d = np.float64(d) # slow
    except Exception:
        logger.error("File '" + filename + "' cannot be opened, not root file ?")
        exit()

    return d, names, n


def load_npy(filename, nmax=-1, shuffle=False):
    """
    Load a PHSP (Phase-Space) file in npy
    Output is numpy structured array
    """

    # Check if file exist
    if not os.path.isfile(filename):
        logger.error("File '" + filename + "' does not exist.")
        exit()

    x = np.load(filename, mmap_mode="r")
    n = len(x)
    if nmax > 0:
        if shuffle:
            x = np.random.choice(x, nmax, replace=False)
        else:
            x = x[:nmax]

    data = x.view(np.float32).reshape(x.shape + (-1,))
    # data = np.float64(data) # slow
    return data, list(x.dtype.names), n


def load(filename, nmax=-1, shuffle=False):
    """
    Load a PHSP (Phase-Space) file
    Output is numpy structured array
    """

    b, extension = os.path.splitext(filename)
    nmax = int(nmax)

    if extension == ".root":
        if shuffle:
            logger.error("cannot shuffle on root file for the moment")
            exit(0)
        return load_root(filename, nmax)

    # if extension == '.raw':
    #     return load_raw(filename)

    if extension == ".npy":
        return load_npy(filename, nmax, shuffle)

    logger.error(
        "dont know how to open phsp with extension ",
        extension,
        " (known extensions: .root .npy)",
    )
    exit(0)


#%%% Generator
def get_noise(n_samples, input_dim, device):
    """
    Function for creating noise vectors: Given the dimensions (n_samples, z_dim)
    creates a tensor of that shape filled with random numbers from the normal distribution.
    Parameters:
      n_samples: the number of samples to generate, a scalar
      z_dim: the dimension of the noise vector, a scalar
      device: the device type
    """
    return torch.randn(n_samples, input_dim, device=device)


def combine_vectors(x, y):
    """
    Function for combining two vectors with shapes (n_samples, ?) and (n_samples, ?).
    Parameters:
      x: (n_samples, ?) the first vector, the noise vector of shape (n_samples, z_dim),
      y: (n_samples, ?) the second vector.
    """
    combined = torch.cat((x.float(), y.float()), dim=1)
    return combined


class Generator(nn.Module):
    """
    Generator Class
    Values:
        z_dim: the dimension of the noise vector, a scalar
        data_dim : the dimension of the real data fed to the critic
    """

    def __init__(self, input_dim, output_dim, hidden_dim, gen_hidden_layers):
        super(Generator, self).__init__()
        self.input_dim = input_dim
        self.gen = nn.Sequential()
        self.gen.add_module("first_layer", nn.Linear(input_dim, hidden_dim))
        # hidden layers
        for i in range(gen_hidden_layers):
            self.gen.add_module(f"activation_{i}", nn.LeakyReLU(0.2))
            self.gen.add_module(f"layer_{i}", nn.Linear(hidden_dim, hidden_dim))
        # last layer
        self.gen.add_module(f"last_layer", nn.Linear(hidden_dim, output_dim))

    def forward(self, noise):
        """
        Function for completing a forward pass of the generator: Given a noise tensor,
        returns generated samples
        Parameters:  noise tensor with dimensions (n_samples, z_dim)
        """
        return self.gen(noise)


def load_generator(Generator, name, data_dimensions, number_of_conditions, device):
    generator_file = torch.load(name)
    z_dim = generator_file.get("z_dim")
    gen_hidden_layers = generator_file.get("gen_hidden_layers")
    g_hidden_dim = generator_file.get("g_hidden_dim")
    generator_input_dim = (
        z_dim + number_of_conditions
    )  # , critic_input_dim = get_input_dimensions(z_dim,data_dimensions,number_of_conditions)
    model = Generator(
        generator_input_dim, data_dimensions, g_hidden_dim, gen_hidden_layers
    ).to(device)
    model.load_state_dict(generator_file.get("state_dict"))
    return model.eval()


def gener_from_data(GAN, bs, conditions_scaler_file, data_scaler_file, phsp_file):

    device = "cpu"
    data_dimensions = 8
    number_of_conditions = 3
    z_dim = 15
    # conditions_scaler_file="/home/asaporta/Desktop/Saves_files_GAN_Jean_ZAY/saved_files_CondGAN_31_08_4cond/Transformers/conditions_scaler_Training_CT_uniforme_1e7kBq_param2.sav"
    conditions_scaler = pickle.load(open(conditions_scaler_file, "rb"))
    # data_scaler_file="/home/asaporta/Desktop/Saves_files_GAN_Jean_ZAY/saved_files_CondGAN_31_08_4cond/Transformers/data_scaler_Training_CT_uniforme_1e7kBq_param2.sav"
    data_scaler = pickle.load(open(data_scaler_file, "rb"))
    # file=os.path.join('/home/asaporta/Desktop/rootfiles', phsp_file)
    name = phsp_file.replace(".root", "")
    data_labels, read_keys_test, samples_number = load(phsp_file, shuffle=False)
    # real_labels=np.concatenate((data_label_energy_scaler.transform(data_labels[:,11:12]),label_position_scaler.transform(data_labels[:,12:15])),axis=1)
    real_labels = conditions_scaler.transform(
        data_labels[:, 1:4]
    )  # juste positions#data_labels[:,8:12])
    Label = Tensor(real_labels).to(device)

    batch_size = int(bs)
    n = len(Label)
    fake_samples = np.empty((0, 8))
    m = 0
    start_time_sec = time.time()

    while m < n:
        cur_batch_size = batch_size
        if cur_batch_size > n - m:
            cur_batch_size = n - m
        # for i in range(int(iterations)):
        noise = get_noise(cur_batch_size, z_dim, device)
        Labels = Label[m : m + cur_batch_size].view(
            cur_batch_size, number_of_conditions
        )
        # Label=Label.view(cur_batch_size,number_of_conditions).to(device)
        noise_labeled = combine_vectors(noise.to(device), Labels)
        # fake = model(noise_labeled).cpu().detach().numpy()
        fake_batch = GAN(noise_labeled).cpu().detach().numpy()  # .cpu().data.numpy()#
        fake_samples = np.concatenate((fake_samples, fake_batch), axis=0)
        m = m + cur_batch_size

    print("fake samples shape : ", fake_samples.shape)
    # fake_samples_total=np.concatenate((data_label_energy_scaler.inverse_transform(fake_samples[:,0:1]),data_position_direction_time_scaler.inverse_transform(fake_samples[:,1:11])),axis=1)
    fake_samples_total = data_scaler.inverse_transform(fake_samples)
    c = scipy.constants.speed_of_light * 1000
    ct_dist = c * fake_samples_total[:, 7:8] / 1e9
    post_dir = fake_samples_total[:, 1:4] + ct_dist * fake_samples_total[:, 4:7]
    reparametrisation = np.concatenate(
        (fake_samples_total[:, 0:1], post_dir, fake_samples_total[:, 4:7]), axis=1
    )  # no need for time
    return reparametrisation
    # print(reparametrisation.shape)
    # reparametrisation=np.concatenate((fake_samples_total[:,0:1],fake_samples_total[:,1:4],fake_samples_total[:,4:]),axis=1)


#%% Generation class


class GANSource_Albert:
    def __init__(self, user_info):
        self.user_info = user_info

    def initialize(self):
        self.user_info.batch_size = int(float(self.user_info.batch_size))

        # self.gan = Box()
        # path_gen="/home/asaporta/Desktop/Saves_files_GAN_Jean_ZAY/saved_files_CondGAN_31_08_4cond/generator/"
        # generator_output_name=path_gen+"generator_199epochs_Training_CT_uniforme_1e7kBq_param2.pth"
        generator_pth_file = self.user_info.pth_filename
        device = "cpu"
        number_of_conditions = 3
        data_dimensions = 8
        self.gan = load_generator(
            Generator, generator_pth_file, data_dimensions, number_of_conditions, device
        )
        GAN = self.gan

    def generator(self, source):

        GAN = self.gan
        # n = self.user_info.batch_size
        start = None
        bs = self.user_info.batch_size
        conditions_scaler_file = self.user_info.condition_scaler_file
        data_scaler_file = self.user_info.data_scaler_file
        phsp_file = self.user_info.condition_root_file
        fake = gener_from_data(
            GAN, bs, conditions_scaler_file, data_scaler_file, phsp_file
        )
        self.copy_generated_particle_to_g4(source, fake)

    def copy_generated_particle_to_g4(self, source, fake):
        mm = gate.g4_units("mm")
        MeV = gate.g4_units("MeV")
        ns = gate.g4_units("ns")

        # get the values from GAN or fixed value
        # the index are precomputed in get_key_generated_values
        # (this is a bit convoluted, but it does the job)
        pos = []
        dir = []
        # dim = len(g.position)

        # position, direction
        # pos.append(fake[:,1:4])
        for i in range(3):

            pos.append(fake[:, i + 1])
            dir.append(fake[:, i + 4])

        # energy
        energy = []
        energy.append(fake[:, 0])
        # weight ? (fake if not used)
        """
        weight = [0]
        if self.user_info.weight_key is not None:
            weight = []
            weight.append(fake[:, g.weight[0]])
            if is_paired:
                weight.append(fake[:, g.weight[1]])

        # time (fake if not used)
        the_time = [0]
        if self.user_info.time_key is not None:
            the_time = []
            the_time.append(fake[:, g.time[0]])
            if is_paired:
                the_time.append(fake[:, g.time[1]])
        """
        # copy to c++
        source.fPositionX = pos[0]
        source.fPositionY = pos[1]
        source.fPositionZ = pos[2]

        # copy to c++
        source.fDirectionX = dir[0]
        source.fDirectionY = dir[1]
        source.fDirectionZ = dir[2]

        source.fEnergy = energy[0]
        # print("DEBUGGGGGGGG",energy[0],pos[2],dir[2])
        # copy to c++
        """
        source.fEnergy = energy[0]
        if self.user_info.weight_key is not None:
            source.fWeight = weight[0]
        if self.user_info.time_key is not None:
            source.fTime = the_time[0]

        """
