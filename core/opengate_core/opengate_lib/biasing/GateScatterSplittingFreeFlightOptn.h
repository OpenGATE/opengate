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

  // Tentative to gain time while preserving precision: all failures
  G4VParticleChange *
  ApplyFinalStateBiasing_V1_PostStepDoIt(const G4BiasingProcessInterface *,
                                         const G4Track *, const G4Step *,
                                         G4bool &);
  G4VParticleChange *
  ApplyFinalStateBiasing_V2_SampleSecondaries(const G4BiasingProcessInterface *,
                                              const G4Track *, const G4Step *,
                                              G4bool &);
  G4VParticleChange *
  ApplyFinalStateBiasing_V3_SampleScatter(const G4BiasingProcessInterface *,
                                          const G4Track *, const G4Step *,
                                          G4bool &);
  G4VParticleChange *
  ApplyFinalStateBiasing_V4_SampleComptonOnly(const G4BiasingProcessInterface *,
                                              const G4Track *, const G4Step *,
                                              G4bool &);

  void SetSplittingFactor(G4int splittingFactor);
  void InitializeAAManager(const std::map<std::string, std::string> &user_info);
  void SetInvolvedBiasActor(GateVBiasOptrActor *actor) { fActor = actor; }

  // approximated do not use
  double SampleCompton_Khan_method(double incidentEnergy,
                                   G4ThreeVector &direction);
  double SampleCompton_Butcher_method(double incidentEnergy,
                                      G4ThreeVector &direction);
  double SampleRayleigh(double incidentEnergy, G4ThreeVector &direction);

  G4int fSplittingFactor;
  G4ParticleChange fParticleChange;
  GateAcceptanceAngleManager *fAAManager;
  double *fNbTracks;
  GateUserTrackInformation *fUserTrackInformation;
  GateVBiasOptrActor *fActor = nullptr;
};

#endif
