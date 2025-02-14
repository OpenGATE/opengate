/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateBOptnBremSplitting_h
#define GateBOptnBremSplitting_h 1

#include "G4ParticleChange.hh"
#include "G4VBiasingOperation.hh"

class GateBremsstrahlungSplittingOptn : public G4VBiasingOperation {
public:
  explicit GateBremsstrahlungSplittingOptn(const G4String &name);
  ~GateBremsstrahlungSplittingOptn() override = default;

  const G4VBiasingInteractionLaw *
  ProvideOccurenceBiasingInteractionLaw(const G4BiasingProcessInterface *,
                                        G4ForceCondition &) override;

  G4VParticleChange *ApplyFinalStateBiasing(const G4BiasingProcessInterface *,
                                            const G4Track *, const G4Step *,
                                            G4bool &) override;

  G4double DistanceToApplyOperation(const G4Track *, G4double,
                                    G4ForceCondition *) override;
  G4VParticleChange *GenerateBiasingFinalState(const G4Track *,
                                               const G4Step *) override;

  void SetSplittingFactor(G4int splittingFactor);

  G4int GetSplittingFactor() const;

  G4int fSplittingFactor;
  G4ParticleChange fParticleChange;
};

#endif
