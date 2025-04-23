/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateOptnComptonScatteringSplitting_h
#define GateOptnComptonScatteringSplitting_h 1

#include "../GateAcceptanceAngleManager.h"
#include "../GateHelpers.h"
#include "../GateUserTrackInformation.h"
#include "G4ParticleChange.hh"
#include "G4VBiasingOperation.hh"
#include "GateVBiasOptrActor.h"

class GateScatterSplittingFreeFlightOptn : public G4VBiasingOperation {
public:
  explicit GateScatterSplittingFreeFlightOptn(const G4String &name,
                                              double *nbTracks);

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
  void InitializeAAManager(const py::dict &user_info);
  void SetInvolvedBiasActor(GateVBiasOptrActor *actor) { fActor = actor; }

  G4int fSplittingFactor;
  G4ParticleChange fParticleChange;
  GateAcceptanceAngleManager *fAAManager;
  double *fNbTracks;
  static constexpr bool cScatterSplittingFreeFlightType = true;
  GateUserTrackInformation *fUserTrackInformation;
  GateVBiasOptrActor *fActor = nullptr;
};

#endif
