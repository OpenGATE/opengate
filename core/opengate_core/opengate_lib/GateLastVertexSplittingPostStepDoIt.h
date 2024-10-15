//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
///
#ifndef GateLastVertexSplittingPostStepDoIt_h
#define GateLastVertexSplittingPostStepDoIt_h


#include "G4VEnergyLossProcess.hh"
#include "G4VEmProcess.hh"
#include "G4VParticleChange.hh"
#include "G4eplusAnnihilation.hh"
#include "G4PhysicalConstants.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4Gamma.hh"
#include "G4Electron.hh"
#include "G4Positron.hh"
#include "G4eeToTwoGammaModel.hh"
#include "G4EmBiasingManager.hh"
#include "G4EntanglementAuxInfo.hh"
#include "G4eplusAnnihilationEntanglementClipBoard.hh"
#include "G4EmParameters.hh"
#include "G4PhysicsModelCatalog.hh"
#include <iostream>




class GateBremPostStepDoIt : public G4VEnergyLossProcess {
public :

GateBremPostStepDoIt();

~ GateBremPostStepDoIt();

virtual G4VParticleChange * PostStepDoIt (const G4Track & track, const G4Step &  step) override 
{
  const G4MaterialCutsCouple* couple = step.GetPreStepPoint()->GetMaterialCutsCouple();
  currentCouple = couple;
  G4VParticleChange* particleChange = G4VEnergyLossProcess::PostStepDoIt(track,step);
  return particleChange;
}

virtual G4VParticleChange * AlongStepDoIt (const G4Track & track, const G4Step &  step) override 
{
  isIonisation = true;
  G4VParticleChange* particleChange = G4VEnergyLossProcess::AlongStepDoIt(track,step);
  return particleChange;
}


};


class GateGammaEmPostStepDoIt : public G4VEmProcess {
public :

GateGammaEmPostStepDoIt();

~ GateGammaEmPostStepDoIt();

virtual G4VParticleChange * PostStepDoIt(const G4Track & track, const G4Step & step) override 
{
  const G4MaterialCutsCouple* couple = step.GetPreStepPoint()->GetMaterialCutsCouple();
  currentCouple = couple;
  G4VParticleChange* particleChange = G4VEmProcess::PostStepDoIt(track,step);
  return particleChange;
}


};

class GateplusannihilAtRestDoIt : public G4eplusAnnihilation {
public :

GateplusannihilAtRestDoIt();
~ GateplusannihilAtRestDoIt();

virtual G4VParticleChange* AtRestDoIt(const G4Track& track,
						   const G4Step& step) override
// Performs the e+ e- annihilation when both particles are assumed at rest.
  {
  G4Track copyTrack = G4Track(track);
  copyTrack.SetStep(&step);
  G4VParticleChange* particleChange = G4eplusAnnihilation::AtRestDoIt(copyTrack,step);
  return particleChange;
  }
};
#endif





  