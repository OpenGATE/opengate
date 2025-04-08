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

#include <pybind11/stl.h>

namespace py = pybind11;

class GateTLEDoseActor : public GateDoseActor {

public:
  // Constructor
  explicit GateTLEDoseActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void BeginOfEventAction(const G4Event *event) override;

  void PreUserTrackingAction(const G4Track *track) override;

  void SetTLETrackInformationOnSecondaries(G4Step* step, G4bool info,G4int nbSec);

  void InitializeCSDAForNewGamma(G4bool isFirstStep,G4Step* step);

  G4double FindEkinMaxForTLE();


  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  // Kill the gamma if below this energy
  double fEnergyMin;

  // Conventional DoseActor if above this energy
  double fMaxRange;

  std::string fDatabase;

  G4EmCalculator* fEmCalc = nullptr; 

  struct threadLocalT {
    // Bool if current track is a TLE gamma or not
    bool fIsTLEGamma =false ;
    bool fIsTLESecondary  = false;
    bool fIsFirstStep = false;
    G4double fCsda = 0 ;
    G4String fPreviousMatName;
    std::map<G4int,std::vector<G4bool>> fSecWhichDeposit; 
  };
  G4Cache<threadLocalT> fThreadLocalData;

  // Database of mu
  std::shared_ptr<GateMaterialMuHandler> fMaterialMuHandler;
};

#endif // GateTLEDoseActor_h
