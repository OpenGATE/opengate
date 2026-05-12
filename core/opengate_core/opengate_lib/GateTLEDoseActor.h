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
#include "GateVAuxiliaryAttribute.h"

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"

#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Dose actor with Track Length Estimator (TLE) scoring support for gammas.
 *
 * During the current transition period, two internal TLE state mechanisms are
 * supported:
 * - "legacy": actor-local logic based on GateUserTrackInformation
 * - "auxiliary": simulation-level GateTLETrackModeAttribute consumed as a
 *   runtime attribute
 *
 * The scoring math itself is intentionally kept local to the actor in this
 * first refactor pass. Only the track/genealogy state logic is being moved out
 * so that the legacy and auxiliary paths can be compared directly.
 */
class GateTLEDoseActor : public GateDoseActor {

public:
  // Constructor
  explicit GateTLEDoseActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;

  void BeginOfEventAction(const G4Event *event) override;

  void PreUserTrackingAction(const G4Track *track) override;

  // LEGACY: actor-local GateUserTrackInformation path kept temporarily for
  // regression testing against the new auxiliary-attribute implementation.
  void SetTLETrackInformationOnSecondaries(G4Step *step, G4bool info,
                                           G4int nbSec);

  void InitializeCSDAForNewGamma(G4bool isFirstStep, G4Step *step);

  G4double FindEkinMaxForTLE();

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;
  // LEGACY: actor-local TLE state logic kept for regression testing only.
  void SteppingActionLegacy(G4Step *step);
  // AUXILIARY: consume a GateTLETrackModeAttribute resolved at initialization.
  void SteppingActionAuxiliary(G4Step *step);
  // Shared TLE deposition kernel used by both legacy and auxiliary state
  // mechanisms.
  void ScoreTLEDepositStep(G4Step *step);

  // Kill the gamma if below this energy
  double fEnergyMin;
  double fEnergyMax;

  // Conventional DoseActor if above this energy
  double fTLEThreshold;

  std::string fDatabase;

  G4EmCalculator *fEmCalc = nullptr;
  G4String fStrTLEThresholdType;
  G4int fTLEThresholdType;
  // Select whether TLE state comes from the legacy actor-local path or the
  // auxiliary-attribute mechanism.
  std::string fTLEStateMode;
  std::string fTLEStateAttributeName;
  GateVAuxiliaryAttribute *fTLEStateAttribute = nullptr;

  struct threadLocalT {
    // LEGACY: actor-local TLE state kept for the temporary legacy mode only.
    // Bool if current track is a TLE gamma or not
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
