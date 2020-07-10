from box import Box

import gam  # needed for gam_setup
import gam_g4 as g4


class Source(g4.G4VUserPrimaryGeneratorAction):
    """
    TODO
    """

    def __init__(self, sources):
        """
        TODO
        """
        g4.G4VUserPrimaryGeneratorAction.__init__(self)

        # 'sources' contains the description of all sources
        # FIXME DO IT LATER
        # create source according to 'sources'
        self.sources = sources

        print('MyPrimaryGeneratorAction constructor')
        self.particle_gun = g4.G4ParticleGun(1)
        print(f'particle_gun {self.particle_gun}')

        self.particle_table = g4.G4ParticleTable.GetParticleTable()
        self.particle_table.CreateAllParticles()
        print(f'particle_table {self.particle_table.size()}')

        # self.particle_table.DumpTable('ALL')

        self.particle = self.particle_table.FindParticle(particle_name="proton")
        #self.particle = self.particle_table.FindParticle(particle_name="gamma")
        print(f'particle {self.particle}')
        if not self.particle:
            print('ERROR particle')
            exit(0)
        print(f'particle {self.particle.GetParticleName()}')

        self.particle_gun.SetParticleDefinition(self.particle)
        self.particle_gun.SetParticleMomentumDirection(g4.G4ThreeVector(0., 0., 1.))
        MeV = gam.g4_units('MeV')
        self.particle_gun.SetParticleEnergy(150.0*MeV)
        #self.particle_gun.SetParticleEnergy(0.1 * MeV)

    def __del__(self):
        print(f'destructor Source')

    def GeneratePrimaries(self, event):
        #print('GeneratePrimaries event=', event)
        cm = gam.g4_units('centimeter')
        diameter = 6*cm
        x0 = diameter * (g4.G4UniformRand() - 0.5)
        y0 = diameter * (g4.G4UniformRand() - 0.5)
        z0 = 0  # -0.5 * 200
        # print('x y z', x0, y0, z0)
        self.particle_gun.SetParticlePosition(g4.G4ThreeVector(x0, y0, z0))
        self.particle_gun.GeneratePrimaryVertex(event)
        # print('end GeneratePrimaries')
