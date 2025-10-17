/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateGammaFreeFlightOptn_h
#define GateGammaFreeFlightOptn_h

#include "../GateVActor.h"
#include "G4ILawForceFreeFlight.hh"
#include "G4ParticleChange.hh"
#include "G4VBiasingOperation.hh"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
   This is based on a copy of G4BOptnForceFreeFlight (Feb 2025).

   When several processes are biased, the weights are not correct,
   The function AlongMoveBy is applied once for each process to cumulate
   the weights, but ApplyFinalStateBiasing is also applied once per process
   re-applying the weights each time.
 */

class GateGammaFreeFlightOptn : public G4VBiasingOperation {
public:
  explicit GateGammaFreeFlightOptn(const G4String &name);
  ~GateGammaFreeFlightOptn() override;

  const G4VBiasingInteractionLaw *
  ProvideOccurenceBiasingInteractionLaw(const G4BiasingProcessInterface *,
                                        G4ForceCondition &) override;
  void AlongMoveBy(const G4BiasingProcessInterface *, const G4Step *,
                   G4double) override;
  G4VParticleChange *ApplyFinalStateBiasing(const G4BiasingProcessInterface *,
                                            const G4Track *, const G4Step *,
                                            G4bool &) override;

  G4double DistanceToApplyOperation(const G4Track *, G4double,
                                    G4ForceCondition *) override;

  G4VParticleChange *GenerateBiasingFinalState(const G4Track *,
                                               const G4Step *) override;

  void ResetInitialTrackWeight(G4double w);

  std::map<int, double> fProcessTypeToWeight;
  G4ILawForceFreeFlight *fForceFreeFlightInteractionLaw = nullptr;
  double fProposedWeight = -1.0;
  G4ParticleChange fParticleChange;
  G4bool fOperationComplete = true;
};

#endif
