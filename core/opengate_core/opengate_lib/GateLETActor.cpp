/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateLETActor.h"
#include "GateHelpersDict.h"

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
