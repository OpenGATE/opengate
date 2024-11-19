/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTLEDoseActor_h
#define GateTLEDoseActor_h

#include "GateDoseActor.h"
#include "GateMaterialMuHandler.h"

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"

#include <pybind11/stl.h>

namespace py = pybind11;

class GateTLEDoseActor : public GateDoseActor {

public:
  // Constructor
  explicit GateTLEDoseActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void BeginOfEventAction(const G4Event* event) override;

  void PreUserTrackingAction(const G4Track *track) override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  // Kill the gamma if below this energy
  double fEnergyMin;

  // Conventional DoseActor if above this energy
  double fEnergyMax;

  struct threadLocalT {
    // Bool if current track is a TLE gamma or not
    bool fIsTLEGamma;
    bool fIsTLESecondary;
    std::map<G4int,G4int> fSecNbWhichDeposit;

  };
  G4Cache<threadLocalT> fThreadLocalData;

  // Database of mu
  std::shared_ptr<GateMaterialMuHandler> fMaterialMuHandler;
};

#endif // GateTLEDoseActor_h
