/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateOptnComptonScatteringSplitting_h
#define GateOptnComptonScatteringSplitting_h 1

#include "G4ParticleChange.hh"
#include "G4VBiasingOperation.hh"
#include "GateAcceptanceAngleTesterManager.h"
#include "GateHelpers.h"

class GateOptnComptonScatteringSplitting : public G4VBiasingOperation {
public:
  explicit GateOptnComptonScatteringSplitting(G4String name);

  const G4VBiasingInteractionLaw *
  ProvideOccurenceBiasingInteractionLaw(const G4BiasingProcessInterface *,
                                        G4ForceCondition &) override;

  G4double DistanceToApplyOperation(const G4Track *, G4double,
                                    G4ForceCondition *) override;
  G4VParticleChange *GenerateBiasingFinalState(const G4Track *,
                                               const G4Step *) override;
  G4VParticleChange *ApplyFinalStateBiasing(const G4BiasingProcessInterface *,
                                            const G4Track *, const G4Step *,
                                            G4bool &) override;

  void SetSplittingFactor(G4int splittingFactor);
  void InitializeAAManager(py::dict user_info);

  G4int fSplittingFactor;
  G4ParticleChange fParticleChange;
  GateAcceptanceAngleTesterManager *fAAManager;
};

#endif
