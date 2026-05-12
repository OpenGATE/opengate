/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTLETrackModeAttribute_h
#define GateTLETrackModeAttribute_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "GateAuxiliaryTrackInformation.h"
#include "GateMaterialMuHandler.h"
#include "GateVAuxiliaryAttribute.h"

#include <memory>

/*
 * Auxiliary attribute that centralizes TLE track-state policy.
 *
 * The attribute owns the TLE decision parameters (threshold type/value,
 * database, low-energy kill threshold), evaluates whether a gamma should enter
 * the Track Length Estimator path, and propagates the resulting state to
 * secondaries through per-track auxiliary information.
 *
 * Public value semantics:
 *   0 = conventional scoring path
 *   1 = TLE gamma scoring path
 *   2 = suppressed secondary (skip conventional deposition)
 *
 * This first-pass design intentionally exposes one integer mode rather than
 * multiple lower-level flags so that actors can consume a single runtime
 * attribute while legacy and auxiliary implementations are cross-tested.
 *
 * The effective mode for the current step can be queried before the attribute's
 * explicit SteppingAction runs. The base-class current-step cache keeps that
 * evaluation consistent so the later SteppingAction can reuse it and perform
 * only the real side effects: track-state storage and secondary propagation.
 */
class GateTLETrackModeAttribute : public GateVAuxiliaryAttribute {
public:
  enum TLETrackMode {
    kConventional = 0,
    kTLEGamma = 1,
    kSuppressedSecondary = 2
  };

  explicit GateTLETrackModeAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  void PreUserTrackingAction(const G4Track *track) override;
  void SteppingAction(const G4Step *step) override;
  int GetIValue(const G4Step *step) const override;
  double GetEnergyMin() const { return fEnergyMin; }
  double GetTLEThreshold() const { return fTLEThreshold; }
  G4int GetTLEThresholdType() const { return fTLEThresholdType; }
  const std::string &GetDatabase() const { return fDatabase; }
  const std::string &GetVolumeName() const { return fVolumeName; }

protected:
  // Runtime initialisation is performed lazily because the EM calculator and
  // mu database are not reliably ready before the simulation starts tracking.
  void EnsureRuntimeInitialized() const;
  G4double FindEkinMaxForTLE() const;
  void InitializeCSDAForNewGamma(bool isFirstStep, const G4Step *step) const;
  bool ComputeTLEConditionForGamma(const G4Step *step) const;
  int ComputeEffectiveModeForStep(const G4Step *step) const;

  double fEnergyMin;
  double fTLEThreshold;
  std::string fDatabase;
  std::string fVolumeName;
  G4String fStrTLEThresholdType;
  G4int fTLEThresholdType;
  mutable G4EmCalculator *fEmCalc = nullptr;
  mutable std::shared_ptr<GateMaterialMuHandler> fMaterialMuHandler;

  struct threadLocalT {
    // Cache used only to avoid repeating expensive CSDA-related work while a
    // gamma is tracked through successive steps in the same thread.
    bool fIsFirstStep = false;
    G4double fCsda = 0;
    G4String fPreviousMatName;
    G4double fPreviousEnergy = -1.0;
  };
  mutable G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateTLETrackModeAttribute_h
