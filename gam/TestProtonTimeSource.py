import gam
import gam_g4 as g4
import numpy as np


class TestProtonTimeSource(gam.SourceBase):
    """
     FIXME
    """

    def __init__(self, source_info):
        """
        TODO
        """
        gam.SourceBase.__init__(self, source_info)

        # timing
        if 'activity' not in source_info:
            gam.fatal(f'The source must have a "activity" key in {source_info}')
        if 'energy' not in source_info:
            gam.fatal(f'The source must have a "energy" key in {source_info}')
        if 'diameter' not in source_info:
            gam.fatal(f'The source must have a "diameter" key in {source_info}')

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
        self.particle_gun.SetParticleEnergy(source_info.energy)
        self.particle_gun.SetParticleTime(0.0)

    def __str__(self):
        s = gam.SourceBase.__str__(self)
        s += f'\nActivity           : {self.source_info.activity/self.Bq:0.1f} Bq'
        return s

    def get_estimated_number_of_events(self, run_timing_interval):
        duration = run_timing_interval[1] - run_timing_interval[0]
        n = self.source_info.activity / self.Bq * duration / self.sec
        return n

    def get_next_event_info(self, current_time):
        # print('TestProtonTimeSource get_next_event_info', current_time, self.sec, self.source_info.activity)
        # print('TestProtonTimeSource get_next_event_info', current_time/self.sec, self.sec,
        #      self.source_info.activity/self.Bq)

        # this source manage the time (activity)
        # regular one here, could either be random
        next_time = current_time + 1.0 / self.source_info.activity
        # print('next time', next_time, next_time/self.sec)
        return next_time, self.shot_event_count + 1

    def GeneratePrimaries(self, event, sim_time):
        # print('GeneratePrimaries event=', event)
        diameter = self.source_info.diameter
        x0 = diameter * (g4.G4UniformRand() - 0.5)
        y0 = diameter * (g4.G4UniformRand() - 0.5)
        z0 = 0  # -0.5 * 200
        # print('x y z', x0, y0, z0)
        self.particle_gun.SetParticlePosition(g4.G4ThreeVector(x0, y0, z0))
        self.particle_gun.SetParticleTime(sim_time)
        self.particle_gun.GeneratePrimaryVertex(event)
        self.shot_event_count += 1
