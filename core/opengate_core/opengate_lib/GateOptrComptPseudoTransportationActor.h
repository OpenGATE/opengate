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
/// \file GateOptrComptPseudoTransportationActor.h
/// \brief Definition of the GateOptrComptPseudoTransportationActor class
#ifndef GateOptrComptPseudoTransportationActor_h
#define GateOptrComptPseudoTransportationActor_h 1

#include "G4EmCalculator.hh"
#include "G4VBiasingOperator.hh"
#include "GateOptnForceFreeFlight.h"
#include "GateOptnPairProdSplitting.h"
#include "GateOptneBremSplitting.h"

#include "GateVActor.h"
#include <iostream>
#include <pybind11/stl.h>
namespace py = pybind11;

class GateOptnScatteredGammaSplitting;

class GateOptrComptPseudoTransportationActor : public G4VBiasingOperator,
                                               public GateVActor {
public:
  GateOptrComptPseudoTransportationActor(py::dict &user_info);
  virtual ~GateOptrComptPseudoTransportationActor() {}

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
  G4double fInitialWeight;
  G4double fRelativeMinWeightOfParticle;
  G4double fWeightThreshold;
  G4bool fBiasPrimaryOnly;
  G4bool fBiasOnlyOnce;
  G4int fNInteractions = 0;
  G4bool fRussianRouletteForAngle;
  G4bool fRussianRouletteForWeights;
  G4bool fRotationVectorDirector;
  G4ThreeVector fVectorDirector;
  G4double fMaxTheta;
  G4bool isSplitted;
  G4int NbOfTrack = 0;
  G4int NbOfProbe = 1;
  G4double weight = 0;
  G4bool fKillOthersParticles = false;
  G4bool fUseProbes = false;
  G4bool fSurvivedRR = false;
  G4bool fAttachToLogicalHolder = true;
  G4bool fPassedByABiasedVolume = false;
  G4double fKineticEnergyAtTheEntrance;
  G4int ftrackIDAtTheEntrance;
  G4int fEventID;
  G4double fEventIDKineticEnergy;
  G4bool ftestbool = false;
  G4bool fIsFirstStep = false;
  const G4VProcess *fAnnihilation = nullptr;

  std::vector<G4String> fNameOfBiasedLogicalVolume = {};
  std::vector<G4int> v_EventID = {};
  std::vector<G4String> fCreationProcessNameList = {
      "biasWrapper(compt)", "biasWrapper(eBrem)", "biasWrapper(annihil)"};

  // Unused but mandatory

  virtual void StartSimulationAction();
  virtual void StartRun();
  virtual void StartTracking(const G4Track *);
  virtual void SteppingAction(G4Step *);
  virtual void BeginOfEventAction(const G4Event *);
  virtual void EndTracking();

protected:
  // -----------------------------
  // -- Mandatory from base class:
  // -----------------------------
  // -- Unused:
  void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *);
  virtual G4VBiasingOperation *ProposeNonPhysicsBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */) {
    return 0;
  }

  // -- Used:
  virtual G4VBiasingOperation *ProposeOccurenceBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */);

  virtual G4VBiasingOperation *ProposeFinalStateBiasingOperation(
      const G4Track *track, const G4BiasingProcessInterface *callingProcess);

private:
  // -- Avoid compiler complaining for (wrong) method shadowing,
  // -- this is because other virtual method with same name exists.
  using G4VBiasingOperator::OperationApplied;

private:
  GateOptnForceFreeFlight *fFreeFlightOperation;
  GateOptnScatteredGammaSplitting *fScatteredGammaSplittingOperation;
  GateOptneBremSplitting *feBremSplittingOperation;
  GateOptnPairProdSplitting *fPairProdSplittingOperation;
};

#endif
