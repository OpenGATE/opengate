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
#include <G4Cache.hh>
#include <G4EmCalculator.hh>
#include <memory>
#include <pybind11/stl.h>

namespace py = pybind11;

/* Dose actor with Track Length Estimator (TLE) scoring support for gammas. */
class GateTLEDoseActor : public GateDoseActor {

public:
  // Constructor
  explicit GateTLEDoseActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;

  void BeginOfEventAction(const G4Event *event) override;

  void PreUserTrackingAction(const G4Track *track) override;

  void SetTLETrackInformationOnSecondaries(G4Step *step, G4bool info,
                                           G4int nbSec);

  void InitializeCSDAForNewGamma(G4bool isFirstStep, G4Step *step);

  G4double FindEkinMaxForTLE();

  // G4EmCalculator is stateful: one instance per thread
  G4EmCalculator &GetEmCalc();

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;
  void ScoreTLEDepositStep(G4Step *step);

  // Deposit edep along the step segment: each dose voxel crossed by the
  // segment gets edep x (length in the voxel / step length). Exact for a
  // gamma step: energy, mu_en/rho and density are constant along the step.
  void ScoreTLEDepositSplit(G4Step *step, double edep, double density,
                            int event_id);

  // If true, the TLE deposit of a step is split among the dose voxels it
  // crosses (see ScoreTLEDepositSplit); otherwise it goes to one voxel,
  // chosen with hit_type.
  bool fSplitStepInVoxels = false;

  // Kill the gamma if below this energy
  double fEnergyMin;
  double fEnergyMax;

  // Conventional DoseActor if above this energy
  double fTLEThreshold;

  std::string fDatabase;

  G4String fStrTLEThresholdType;
  G4int fTLEThresholdType;
  int fLegacyTLETrackDataSlotID{-1};

  struct threadLocalT {
    std::unique_ptr<G4EmCalculator> fEmCalc;
    bool fIsTLEGamma = false;
    bool fIsTLESecondary = false;
    bool fIsFirstStep = false;
    G4double fCsda = 0;
    G4String fPreviousMatName;
    G4double fPreviousEnergy;
    std::map<G4int, std::vector<G4bool>> fSecWhichDeposit;
  };
  G4Cache<threadLocalT> fThreadLocalData;

  // Database of mu
  std::shared_ptr<GateMaterialMuHandler> fMaterialMuHandler;
};

#endif // GateTLEDoseActor_h
