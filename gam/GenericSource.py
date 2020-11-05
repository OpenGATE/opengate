import gam
import gam_g4 as g4
import numpy as np


class GenericSource(gam.SourceBase):
    """
      FIXME
        - particle type: gamma, proton, e-, etc
        - position: point, shape, etc
        - direction: vector, gauss, min-max etc
        - energy: mono, gauss, histo etc
        - activity

    """

    type_name = 'GenericSource'

    def __init__(self, name):
        gam.SourceBase.__init__(self, name)
        self.Bq = gam.g4_units('Bq')
        MeV = gam.g4_units('MeV')
        self.sec = gam.g4_units('s')
        self.user_info.particle = 'gamma'
        self.user_info.energy = 1 * MeV
        self.user_info.position = None
        self.user_info.direction = None
        self.user_info.activity = 1 * self.Bq
        # G4 objects
        self.particle_gun = None
        self.particle = None
        # FIXME
        self.position = None
        self.direction = None
        self.next_time = -1

    def __str__(self):
        # FIXME
        s = gam.SourceBase.__str__(self)
        # s += f'\nActivity           : {self.user_info.activity / self.Bq:0.1f} Bq'
        # s += f'\nEnergy             : {g4.G4BestUnit(self.user_info.energy, "Energy")}'
        # s += f'\nRadius             : {g4.G4BestUnit(self.user_info.radius, "Length")}'
        # s += f'\nTranslation        : {self.user_info.translation}'
        s += 'TODO'
        return s

    def __del__(self):
        print('destructor GenericSource')

    def initialize(self, run_timing_intervals):
        gam.SourceBase.initialize(self, run_timing_intervals)
        self.particle_gun = g4.G4ParticleGun(1)
        p = self.user_info.particle
        self.particle = self.particle_table.FindParticle(particle_name=p)
        if not self.particle:
            gam.fatal(f'Cannot find the particle {p} for this source: {self.user_info}')
        self.particle_gun.SetParticleDefinition(self.particle)

        # first time
        t = run_timing_intervals[0][0]
        self.next_time = t + -np.log(g4.G4UniformRand()) * (1.0 / self.user_info.activity)

        # position
        self.position = self.user_info.position.object
        self.position.initialize()

        # direction
        self.direction = self.user_info.direction.object
        self.direction.initialize()
        ## FIXME ! G4SPSPosDistribution needed
        self.direction.generator.SetPosDistribution(self.position.generator)

    def get_estimated_number_of_events(self, run_timing_interval):
        duration = run_timing_interval[1] - run_timing_interval[0]
        n = self.user_info.activity / self.Bq * duration / self.sec
        return n

    def source_is_terminated(self, sim_time):
        # Check if the source is terminated with the future time
        # (this prevent to have an empty Event)
        if self.next_time > self.user_info.end_time:
            return True
        return False

    def get_next_event_info(self, current_time):
        # if the next time is in the future, we are still return the current next time
        if current_time < self.next_time:
            return self.next_time, self.shot_event_count + 1
        # if this is not the case, we plan a new 'next time'
        self.next_time = current_time + -np.log(g4.G4UniformRand()) * (1.0 / self.user_info.activity)
        return self.next_time, self.shot_event_count + 1

    def generate_primaries(self, event, sim_time):
        # sec = gam.g4_units('s')
        # print('GeneratePrimaries event=', self.user_info.name, sim_time / sec)

        # time
        self.particle_gun.SetParticleTime(sim_time)

        # position
        pos = self.position.shoot()
        self.particle_gun.SetParticlePosition(pos)

        # direction
        dir = self.direction.shoot()
        self.particle_gun.SetParticleMomentumDirection(dir)

        # energy
        self.particle_gun.SetParticleEnergy(self.user_info.energy)

        # radius = self.user_info.radius
        # x0 = radius * (g4.G4UniformRand() - 0.5)
        # y0 = radius * (g4.G4UniformRand() - 0.5)
        # length = np.sqrt(g4.G4UniformRand()) * radius
        # angle = np.pi * g4.G4UniformRand() * 2
        # x0 = length * np.cos(angle) + self.user_info.translation[0]
        # y0 = length * np.sin(angle) + self.user_info.translation[1]

        # z0 = self.user_info.translation[2]
        # print('x y z', x0, y0, z0)
        # self.particle_gun.SetParticlePosition(g4.G4ThreeVector(x0, y0, z0))

        self.particle_gun.GeneratePrimaryVertex(event)
        self.shot_event_count += 1
