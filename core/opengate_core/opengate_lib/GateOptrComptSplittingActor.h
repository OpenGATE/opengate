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
///
/// \file GateOptrComptSplittingActor.h
/// \brief Definition of the GateOptrComptSplittingActor class
#ifndef GateOptrComptSplittingActor_h
#define GateOptrComptSplittingActor_h 1

#include "G4VBiasingOperator.hh"

#include "GateVActor.h"
#include <iostream>
#include <pybind11/stl.h>
namespace py = pybind11;

class GateOptnComptSplitting;

class GateOptrComptSplittingActor : public G4VBiasingOperator,
                                    public GateVActor {
public:
  GateOptrComptSplittingActor(py::dict &user_info);
  virtual ~GateOptrComptSplittingActor() {}

public:
  // -------------------------
  // Optional from base class:
  // -------------------------
  // -- Call at run start:
  // virtual void BeginOfRunAction(const G4Run *run);

  // virtual void SteppingAction(G4Step* step);

  // -- Call at each track starting:
  // virtual void PreUserTrackingAction( const G4Track* track );

  G4double fSplittingFactor;
  G4double fMinWeightOfParticle;
  G4double fWeightThreshold;
  G4bool fBiasPrimaryOnly;
  G4bool fBiasOnlyOnce;
  G4int fNInteractions = 0;
  G4bool fRussianRoulette;
  G4bool fRotationVectorDirector;
  G4ThreeVector fVectorDirector;
  G4double fMaxTheta;
  // Unused but mandatory

  void StartSimulationAction() override;
  void StartRun() override;
  void StartTracking(const G4Track *) override;
  void EndTracking() override {}
  void InitializeUserInput(py::dict &user_info) override;
  void InitializeCpp() override;

protected:
  // -----------------------------
  // -- Mandatory from base class:
  // -----------------------------
  // -- Unused:
  void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *);
  G4VBiasingOperation *ProposeNonPhysicsBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */) override {
    return 0;
  }
  G4VBiasingOperation *ProposeOccurenceBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */) override {
    return 0;
  }

  // -- Used:
  G4VBiasingOperation *ProposeFinalStateBiasingOperation(
      const G4Track *track,
      const G4BiasingProcessInterface *callingProcess) override;

private:
  // -- Avoid compiler complaining about (wrong) method shadowing,
  // -- this is because other virtual method with same name exists.
  using G4VBiasingOperator::OperationApplied;

private:
  GateOptnComptSplitting *fComptSplittingOperation;
};

#endif
