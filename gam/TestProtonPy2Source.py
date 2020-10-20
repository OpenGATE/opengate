import gam
import gam_g4 as g4
import numpy as np


class TestProtonPy2Source(gam.SourceBase):
    """
     FIXME: this is a test
    """

    source_type = 'TestProtonPy2'

    def __init__(self, name):
        gam.SourceBase.__init__(self, name)
        # default user parameter values
        MeV = gam.g4_units('MeV')
        cm = gam.g4_units('cm')
        self.user_info.n = 1
        self.user_info.energy = 150 * MeV
        self.user_info.diameter = 10 * cm
        # set the max number of particle to shoot
        self.total_particle_count = self.user_info.n
        self.particle_gun = None
        self.particle_table = None
        self.particle = None

    def initialize(self, run_timing_intervals):
        gam.SourceBase.initialize(self, run_timing_intervals)
        # create  generator
        self.particle_gun = g4.G4ParticleGun(1)
        self.particle_table = g4.G4ParticleTable.GetParticleTable()
        self.particle_table.CreateAllParticles()
        self.particle = self.particle_table.FindParticle(particle_name="proton")
        if not self.particle:
            print('ERROR particle')
            exit(0)
        self.particle_gun.SetParticleDefinition(self.particle)
        self.particle_gun.SetParticleMomentumDirection(g4.G4ThreeVector(0., 0., 1.))
        self.particle_gun.SetParticleEnergy(self.user_info.energy)
        self.particle_gun.SetParticleTime(0.0)

    def get_next_event_info(self, current_time):
        # this source does not manage the time, only the nb of particle
        # so whatever the current_time, we consider 0
        return self.user_info.start_time, self.shot_event_count + 1

    def generate_primaries(self, event, sim_time):
        diameter = self.user_info.diameter
        # x0 = diameter * (g4.G4UniformRand() - 0.5)
        # y0 = diameter * (g4.G4UniformRand() - 0.5)
        length = np.sqrt(g4.G4UniformRand()) * diameter / 2.0
        angle = 2 * np.pi * g4.G4UniformRand()
        x0 = length * np.cos(angle)
        y0 = length * np.sin(angle)
        z0 = 0  # -0.5 * 200
        # print('x y z', x0, y0, z0)
        self.particle_gun.SetParticlePosition(g4.G4ThreeVector(x0, y0, z0))
        self.particle_gun.GeneratePrimaryVertex(event)
        # print('end GeneratePrimaries')
        # self.particle_gun.SetParticleTime(self.current_time)
        self.shot_event_count += 1
