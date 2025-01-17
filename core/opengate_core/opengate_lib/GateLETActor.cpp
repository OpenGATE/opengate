/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateLETActor.h"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "G4Deuteron.hh"
#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4Positron.hh"
#include "G4Proton.hh"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetLETPixelMutex = G4MUTEX_INITIALIZER;

G4Mutex SetLETNbEventMutex = G4MUTEX_INITIALIZER;

GateLETActor::GateLETActor(py::dict &user_info)
    : GateWeightedEdepActor(user_info) {}

void GateLETActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method

  GateWeightedEdepActor::InitializeUserInfo(user_info);

  fAveragingMethod = DictGetStr(user_info, "averaging_method");
  doTrackAverage = (fAveragingMethod == "track_average");
}

double GateLETActor::ScoringQuantityFn(G4Step *step, double *secondQuantity){
  // get edep in MeV (take weight into account)
  auto w = step->GetTrack()->GetWeight();
  auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
  double dedx_cut = DBL_MAX;

  auto *current_material = step->GetPreStepPoint()->GetMaterial();
  auto density = current_material->GetDensity() / CLHEP::g * CLHEP::cm3;
  const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();

  auto energy = CalcMeanEnergy(step);

  if (p == G4Gamma::Gamma()) {
    p = G4Electron::Electron();
  }
  auto &l = fThreadLocalData.Get();
  auto dedx_currstep =
      l.emcalc.ComputeElectronicDEDX(energy, p, current_material, dedx_cut) /
      CLHEP::MeV * CLHEP::mm;

  if (fScoreInOtherMaterial) {
    auto SPR_otherMaterial = GetSPROtherMaterial(step, energy);
    if (!std::isnan(SPR_otherMaterial)) {
      edep *= SPR_otherMaterial;
      dedx_currstep *= SPR_otherMaterial;
    }
  }
   return dedx_currstep;
   }

// void GateLETActor::SteppingAction(G4Step *step) {
//   // Get the voxel index
//   G4ThreeVector position;
//   bool isInside;
//   Image3DType::IndexType index;
//   GetVoxelPosition(step, position, isInside, index);
//   
//    if (!isInside) {return;}
//       
//   auto dedx_currstep = ScoringQuantityFn(step);
// 
//   double scor_val_num = 0.;
//   double scor_val_den = 0.;
// 
//   if (fAveragingMethod == "dose_average") {
//     scor_val_num = edep * dedx_currstep / CLHEP::MeV / CLHEP::MeV * CLHEP::mm;
//     scor_val_den = edep / CLHEP::MeV;
//   } else if (fAveragingMethod == "track_average") {
//     auto steplength = step->GetStepLength() / CLHEP::mm;
//     scor_val_num = steplength * dedx_currstep * w / CLHEP::MeV;
//     scor_val_den = steplength * w / CLHEP::mm;
//   }
//   // Call ImageAddValue() in a mutexed {}-scope
//   {
//     G4AutoLock mutex(&SetLETPixelMutex);
//     ImageAddValue<Image3DType>(cpp_numerator_image, index, scor_val_num);
//     ImageAddValue<Image3DType>(cpp_denominator_image, index, scor_val_den);
//   }
// } // else : outside the image
