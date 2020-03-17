#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geant4 as g4

class MyPrimaryGeneratorAction(g4.G4VUserPrimaryGeneratorAction):
    """
    Primary Generator
    """

    def __init__(self):
        print('MyPrimaryGeneratorAction constructor')
        self.particle_gun  = g4.G4ParticleGun(1)
        print(f'particle_gun {self.particle_gun}')

        self.particle_table = g4.G4ParticleTable.GetParticleTable()
        print(f'particle_table {self.particle_table}')

        self.particle = self.particle_table.FindParticle(particle_name="gamma")
        print(f'particle {self.particle} {self.particle.GetParticleName()}')

        self.particle_gun.SetParticleDefinition(self.particle)
        self.particle_gun.SetParticleMomentumDirection(g4.G4ThreeVector(0.,0.,1.))
        self.particle_gun.SetParticleEnergy(6.0)#.*MeV);

        print(f'end constructor particle_gun {self.particle_gun}')
        

    def GeneratePrimaries(self, event):
        print('GeneratePrimaries event=', event)
        size = 0.8;
        x0 = size * 200 * (g4.G4UniformRand()-0.5)
        y0 = size * 200 * (g4.G4UniformRand()-0.5)
        z0 = -0.5 * 200
        print('x y z', x, y, z)
        particle_gun.SetParticlePosition(G4ThreeVector(x0,y0,z0))
        particle_gun.GeneratePrimaryVertex(event)

        

# --------------------------------------------------------------
# class MyActionInitialization(g4.G4VUserActionInitialization):
#     """
#     Example class to create a G4VUserActionInitialization
#     """

#     def __init__(self):
#         print('Constructor MyAction')

#     def BuildForMaster(self):
#         print('MyAction::BuildForMaster')
        
#     def Build(self):
#         print('MyAction::Build')
#         mpga = MyPrimaryGeneratorAction()
#         self.SetUserAction(mpga)
        
    

# action initialisation
#print('hello world action')
#my_action_init = MyActionInitialization()
#print('end action')
