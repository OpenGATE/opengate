//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
//
/// \file GateOptnVGenericSplitting.h
/// \brief Definition of the GateOptnVGenericSplitting class
//

#ifndef GateOptnVGenericSplitting_h
#define GateOptnVGenericSplitting_h 1

#include "G4ParticleChange.hh"
#include "G4VBiasingOperation.hh"

class GateOptnVGenericSplitting : public G4VBiasingOperation {
public:
  // -- Constructor :
  GateOptnVGenericSplitting(G4String name);

  // -- destructor:
  virtual ~GateOptnVGenericSplitting();

public:
  // ----------------------------------------------
  // -- Methods from G4VBiasingOperation interface:
  // ----------------------------------------------
  // -- Unused:
  virtual const G4VBiasingInteractionLaw *
  ProvideOccurenceBiasingInteractionLaw(const G4BiasingProcessInterface *,
                                        G4ForceCondition &) {
    return 0;
  }

  // --Used:
  virtual G4VParticleChange *
  ApplyFinalStateBiasing(const G4BiasingProcessInterface *, const G4Track *,
                         const G4Step *, G4bool &) {
    return 0;
  };

  // -- Unsued:
  virtual G4double DistanceToApplyOperation(const G4Track *, G4double,
                                            G4ForceCondition *) {
    return DBL_MAX;
  }
  virtual G4VParticleChange *GenerateBiasingFinalState(const G4Track *,
                                                       const G4Step *) {
    return 0;
  }


// ----------------------------------------------
// -- Methods for the generic splitting
// ----------------------------------------------

void TrackInitializationChargedParticle(G4ParticleChange* particleChange,G4VParticleChange* processFinalState, const G4Track* track,G4double split);
void TrackInitializationGamma(G4ParticleChange* particleChange,G4VParticleChange* processFinalState, const G4Track* track,G4double split);
static G4double RussianRouletteForAngleSurvival(G4ThreeVector dir,G4ThreeVector vectorDirector,G4double maxTheta,G4double split);


public:
  // ----------------------------------------------
  // -- Additional methods, specific to this class:
  // ----------------------------------------------
  // -- Splitting factor:
  void SetSplittingFactor(G4double splittingFactor) {
    fSplittingFactor = splittingFactor;
  }
  G4double GetSplittingFactor() const { return fSplittingFactor; }

  void SetRussianRouletteForAngle(G4bool russianRoulette) {
    fRussianRouletteForAngle = russianRoulette;
  }

  void SetVectorDirector(G4ThreeVector vectorDirector) {
    fVectorDirector = vectorDirector;
  }

  void SetRotationMatrix(G4RotationMatrix rot) { fRot = rot; }

  G4ThreeVector GetVectorDirector() const { return fVectorDirector; }

  void SetMaxTheta(G4double maxTheta) { fMaxTheta = maxTheta; }

  G4double GetMaxTheta() const { return fMaxTheta; }

  G4VParticleChange *GetParticleChange() {
    G4VParticleChange *particleChange = &fParticleChange;
    return particleChange;
  }

  G4double fSplittingFactor;
  G4ParticleChange fParticleChange;
  G4bool fRussianRouletteForAngle;
  G4ThreeVector fVectorDirector;
  G4double fMaxTheta;
  G4RotationMatrix fRot;
};

#endif
