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
//
/// \file GateOptrComptSplittingActor.cc
/// \brief Implementation of the GateOptrComptSplittingActor class

#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "CLHEP/Units/SystemOfUnits.h"
#include "G4BiasingProcessInterface.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "GateOptnComptSplitting.h"
#include "GateOptrComptSplittingActor.h"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptrComptSplittingActor::GateOptrComptSplittingActor(py::dict &user_info)
    : G4VBiasingOperator("ComptSplittingOperator"),
      GateVActor(user_info, false) {
  fMotherVolumeName = DictGetStr(user_info, "mother");
  fSplittingFactor = DictGetDouble(user_info, "splitting_factor");
  fWeightThreshold = DictGetDouble(user_info, "weight_threshold");
  fMinWeightOfParticle = DictGetDouble(user_info, "min_weight_of_particle");
  // Since the russian roulette uses as a probablity 1/splitting, we need to
  // have a double, but the splitting factor provided by the user is logically
  // an int, so we need to change the type.
  fRotationVectorDirector = DictGetBool(user_info, "rotation_vector_director");
  fBiasPrimaryOnly = DictGetBool(user_info, "bias_primary_only");
  fBiasOnlyOnce = DictGetBool(user_info, "bias_only_once");
  fRussianRoulette = DictGetBool(user_info, "russian_roulette");
  fVectorDirector = DictGetG4ThreeVector(user_info, "vector_director");
  fMaxTheta = DictGetDouble(user_info, "max_theta");
  fComptSplittingOperation =
      new GateOptnComptSplitting("ComptSplittingOperation");
  fActions.insert("StartSimulationAction");
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void GateOptrComptSplittingActor::AttachAllLogicalDaughtersVolumes(
    G4LogicalVolume *volume) {
  AttachTo(volume);
  G4int nbOfDaughters = volume->GetNoDaughters();
  if (nbOfDaughters > 0) {
    for (int i = 0; i < nbOfDaughters; i++) {
      G4LogicalVolume *logicalDaughtersVolume =
          volume->GetDaughter(i)->GetLogicalVolume();
      AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
    }
  }
}

void GateOptrComptSplittingActor::StartSimulationAction() {
  G4LogicalVolume *biasingVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);

  // Here we need to attach all the daughters and daughters of daughters (...)
  // to the biasing operator. To do that, I use the function
  // AttachAllLogicalDaughtersVolumes.
  AttachAllLogicalDaughtersVolumes(biasingVolume);
  fComptSplittingOperation->SetSplittingFactor(fSplittingFactor);
  fComptSplittingOperation->SetWeightThreshold(fWeightThreshold);
  fComptSplittingOperation->SetMaxTheta(fMaxTheta);
  fComptSplittingOperation->SetRussianRoulette(fRussianRoulette);
  fComptSplittingOperation->SetMinWeightOfParticle(fMinWeightOfParticle);
}

void GateOptrComptSplittingActor::StartRun() {

  // The way to behave of the russian roulette is the following :
  // we provide a vector director and the theta angle acceptance, where theta =
  // 0 is a vector colinear to the vector director Then if the track generated
  // is on the acceptance angle, we add it to the primary track, and if it's not
  // the case, we launch the russian roulette
  if (fRotationVectorDirector) {
    G4VPhysicalVolume *physBiasingVolume =
        G4PhysicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);
    auto rot = physBiasingVolume->GetObjectRotationValue();
    fVectorDirector = rot * fVectorDirector;
  }

  fComptSplittingOperation->SetVectorDirector(fVectorDirector);
}

void GateOptrComptSplittingActor::StartTracking(const G4Track *track) {
  fNInteractions = 0;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4VBiasingOperation *
GateOptrComptSplittingActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  if (fBiasPrimaryOnly && (track->GetParentID() != 0))
    return 0;
  if (fBiasOnlyOnce && (fNInteractions > 0))
    return 0;
  fNInteractions++;
  return fComptSplittingOperation;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
