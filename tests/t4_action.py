#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geant4 as g4

class MyPrimaryGeneratorAction(G4VUserPrimaryGeneratorAction):
    """
    Primary Generator
    """

    def __init__(self):
        print('MyPrimaryGeneratorAction constructor')
        particle_gun  = g4.G4ParticleGun(1)
        particle_table = g4.G4ParticleTable.GetParticleTable()
        particle = particle_table.FindParticle(particleName="gamma")
        self.particle_gun.SetParticleDefinition(particle)
        self.particle_gun.SetParticleMomentumDirection(g4.G4ThreeVector(0.,0.,1.))
        self.particle_gun.SetParticleEnergy(6.0)#.*MeV);

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
class MyActionInitialization(G4VUserActionInitialization):
    """
    Example class to create a G4VUserActionInitialization
    """

    def __init__(self):
        print('Constructor MyAction')

    def BuildForMaster(self):
        print('MyAction::BuildForMaster')
        
    def Build(self):
        print('MyAction::Build')
        mpga = MyPrimaryGeneratorAction()
        self.SetUserAction(mpga)
        
    

# action initialisation
my_action_init = MyActionInitialization()

