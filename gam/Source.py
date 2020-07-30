import gam
import gam_g4 as g4
import numpy as np

class Source:
    def __init__(self):
        print('def const source')
        sec = gam.g4_units('second')
        self.end_time = 1.0 * sec
        self.shoot_particle_counts = 0
        self.max_particle = 20

    def initialize(self, run_time_interval):
        print('source init')
        # check if time or not, according to parameter

    def is_terminated(self, current_time):
        # return self.shoot_particle_counts >= self.max_particle
        return current_time >= self.end_time

    def get_next_proposed_time(self, t):
        # return 0.0
        # sampling interval distribution
        nt = -np.log(g4.G4UniformRand()) * (1. / t)
        print(f'timing {t} -> {nt}')
        return nt

    def prepare_generate_primaries(self, time):
        # if decay, activity is reduced
        print('shoot')

    def GeneratePrimaries(self, event):
