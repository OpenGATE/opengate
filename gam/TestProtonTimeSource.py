import gam
import gam_g4 as g4
import numpy as np


class TestProtonTimeSource(gam.SourceBase):
    """
     FIXME
    """

    type_name = 'TestProtonTime'

    def __init__(self, name):
        gam.SourceBase.__init__(self, name)
        self.Bq = gam.g4_units('Bq')
        MeV = gam.g4_units('MeV')
        cm = gam.g4_units('cm')
        self.sec = gam.g4_units('s')
        self.user_info.translation = [0, 0, 0]
        self.user_info.activity = 1 * self.Bq
        self.user_info.energy = 150 * MeV
        self.user_info.radius = 5 * cm
        # G4 objects
        self.particle_gun = None
        self.particle = None
        self.next_time = None

    def __del__(self):
        print('destructor TestProtonTimeSource')

    def initialize(self, run_timing_intervals):
        gam.SourceBase.initialize(self, run_timing_intervals)
        self.particle_gun = g4.G4ParticleGun(1)
        self.particle = self.particle_table.FindParticle(particle_name="proton")
        if not self.particle:
            print('ERROR particle')
            exit(0)
        self.particle_gun.SetParticleDefinition(self.particle)
        self.particle_gun.SetParticleMomentumDirection(g4.G4ThreeVector(0., 0., 1.))
        self.particle_gun.SetParticleEnergy(self.user_info.energy)
        self.particle_gun.SetParticleTime(0.0)
        self.next_time = self.user_info.start_time  # run_timing_intervals[0][0]

    def get_estimated_number_of_events(self, run_timing_interval):
        # FIXME wrong : start and end times should be considered
        if run_timing_interval[0]:
            duration = run_timing_interval[1] - run_timing_interval[0]
            n = self.user_info.activity / self.Bq * duration / self.sec
            return n
        return 0

    def source_is_terminated(self, current_time):
        # Check if the source is terminated with the future time
        # (this prevent to have an empty Event)
        if self.next_time > self.user_info.end_time:
            return True
        return False

    def get_next_event_info(self, current_time):
        if current_time < self.next_time:
            return self.next_time, self.shot_event_count + 1

        # this source manage the time (activity)
        # regular activity here, could either be random
        # self.next_time = current_time + 1.0 / self.user_info.activity
        self.next_time = current_time + -np.log(g4.G4UniformRand()) * (1.0 / self.user_info.activity)

        # forward time if below the start time of the current run time interval
        # if self.next_time < self.current_run_interval[0]:
        #    self.next_time = self.current_run_interval[0]

        return self.next_time, self.shot_event_count + 1

    def generate_primaries(self, event, sim_time):
        # print('GeneratePrimaries event=', event)
        radius = self.user_info.radius
        # x0 = radius * (g4.G4UniformRand() - 0.5)
        # y0 = radius * (g4.G4UniformRand() - 0.5)
        length = np.sqrt(g4.G4UniformRand()) * radius
        angle = np.pi * g4.G4UniformRand() * 2
        x0 = length * np.cos(angle) + self.user_info.translation[0]
        y0 = length * np.sin(angle) + self.user_info.translation[1]

        z0 = self.user_info.translation[2]
        # print('x y z', x0, y0, z0)
        self.particle_gun.SetParticlePosition(g4.G4ThreeVector(x0, y0, z0))
        self.particle_gun.SetParticleTime(sim_time)
        self.particle_gun.GeneratePrimaryVertex(event)
        self.shot_event_count += 1
