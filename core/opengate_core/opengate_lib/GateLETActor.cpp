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

double GateLETActor::ScoringQuantityFn(G4Step *step, double *secondQuantity) {

  auto &l = fThreadLocalData.Get();
  auto dedx_currstep = l.dedx_currstep;

  if (fScoreInOtherMaterial) {
    auto SPR_otherMaterial = GetSPROtherMaterial(step);

    dedx_currstep *= SPR_otherMaterial;
  }
  return dedx_currstep;
}
