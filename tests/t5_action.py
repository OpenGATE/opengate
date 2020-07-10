#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from t5_source import MyPrimaryGeneratorAction
import gam_g4 as g4
import gam
import numpy as np

class B1RunAction(g4.G4UserRunAction):

    def __init__(self):
        g4.G4UserRunAction.__init__(self)
        print('B1RunAction constructor')

    def BeginOfRunAction(self, run):
        print('B1RunAction BeginOfRunAction', run)


class B1EventAction(g4.G4UserEventAction):

    def __init__(self):
        g4.G4UserEventAction.__init__(self)
        print('B1EventAction constructor')

    def BeginOfEventAction(self, event):
        #print('B1EventAction BeginOfEventAction', event)
        pass


class B1SteppingAction(g4.G4UserSteppingAction):

    # gray = gam.g4_units('gray')
    gray = 1.0000000000000002e-12
    nb_step = 0
    nb_step_wb = 0

    def __init__(self):
        g4.G4UserSteppingAction.__init__(self)
        print('B1SteppingAction constructor')
        n = 100
        self.depth_dose = np.zeros(n)
        print('gray', self.gray)

    def UserSteppingAction(self, step):
        self.nb_step += 1
        pt = step.GetPreStepPoint()
        name = pt.GetPhysicalVolume().GetName()
        if name != "Waterbox":
            return
        self.nb_step_wb += 1
        #print('B1SteppingAction::UserSteppingAction', step)
        edep = step.GetTotalEnergyDeposit()
        #print('edep', edep)
        density = 1.0
        volume = 1.0
        dose = edep / density / volume / self.gray
        depth = 400
        #print(dose, depth, step)
        #print(step.GetPostStepPoint())
        p = step.GetPostStepPoint().GetPosition()
        #print(p)
        # 250-200 to 250+200
        #i = int((p.z-(250-200))/400.0)
        n = len(self.depth_dose)
        i = int((p.z-50)/depth*n)
        if i>n-1:
            i = n-1
        #print(i, name)
        self.depth_dose[i] += dose

    def get_dose(self):
        print('toto', self.gray)
        print('step=', self.nb_step, ' stepwb=', self.nb_step_wb)
        return self.depth_dose


class B1SteppingBatchAction(g4.G4UserSteppingBatchAction):

    # gray = gam.g4_units('gray')
    gray = 1.0000000000000002e-12
    nb_step = 0
    nb_step_wb = 0
    num_batch = 0

    def __init__(self):
        g4.G4UserSteppingBatchAction.__init__(self, 100000)
        print('B1SteppingAction constructor')
        n = 100
        self.depth_dose = np.zeros(n)
        print('gray', self.gray)

    def UserSteppingBatchAction(self):
        #print('UserSteppingBatchAction')
        self.num_batch += 1

    def get_dose(self):
        print('ok END batch', self.num_batch)


class B1ActionInitialization(g4.G4VUserActionInitialization):

    def __init__(self):
        g4.G4VUserActionInitialization.__init__(self)
        print('B1ActionInitialization constructor')

    def BuildForMaster(self):
        print('B1ActionInitialization:BuildForMaster')
        self.runAction = B1RunAction()
        self.SetUserAction(self.runAction)

    def Build(self):
        self.source = MyPrimaryGeneratorAction()
        self.SetUserAction(self.source)

        self.runAction = B1RunAction()
        self.SetUserAction(self.runAction)

        self.eventAction = B1EventAction() #self.runAction)
        self.SetUserAction(self.eventAction)

        self.stepAction = B1SteppingAction()
        #self.stepAction = B1SteppingBatchAction()
        self.SetUserAction(self.stepAction)

    def get_dose(self):
        return self.stepAction.get_dose()
