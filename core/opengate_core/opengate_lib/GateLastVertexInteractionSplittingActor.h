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
/// \file GateLastVertexInteractionSplittingActor.h
/// \brief Definition of the GateLastVertexInteractionSplittingActor class
#ifndef GateLastVertexInteractionSplittingActor_h
#define GateLastVertexInteractionSplittingActor_h 1

#include "G4ParticleChangeForGamma.hh"
#include "G4VEnergyLossProcess.hh"
#include "GateVActor.h"
#include <iostream>
#include <pybind11/stl.h>
#include "GateLastVertexSplittingDataContainer.h"
#include "tree.hh"
#include "tree_util.hh"
#include <iostream>
#include "GateLastVertexSource.h"
#include "CLHEP/Vector/ThreeVector.h"
using CLHEP::Hep3Vector;

namespace py = pybind11;

class GateLastVertexInteractionSplittingActor : public GateVActor {
public:
  GateLastVertexInteractionSplittingActor(py::dict &user_info);
  virtual ~GateLastVertexInteractionSplittingActor() {}

  G4double fSplittingFactor;
  G4bool fAngularKill;
  G4bool fRotationVectorDirector;
  G4ThreeVector fVectorDirector;
  G4double fMaxTheta;
  G4int fTrackIDOfSplittedTrack = 0;
  G4int fParentID = -1;
  G4int fEventID;
  G4int fEventIDOfSplittedTrack;
  G4int fEventIDOfInitialSplittedTrack;
  G4int fTrackIDOfInitialTrack;
  G4int fTrackIDOfInitialSplittedTrack = 0;
  G4int ftmpTrackID;
  G4bool fIsFirstStep = true;
  G4bool fSuspendForAnnihil = false;
  G4double fWeightOfEnteringParticle = 0;
  G4double fSplitCounter = 0;
  G4bool fNotSplitted = true;
  G4String fActiveSource = "None";
  G4bool fIsAnnihilAlreadySplit =false;
  G4int fCounter;
  GateLastVertexSource* fVertexSource = nullptr;
  tree<LastVertexDataContainer> fTree;
  tree<LastVertexDataContainer>::post_order_iterator fIterator;
  std::vector<LastVertexDataContainer> fListOfContainer;


  G4Track *fTrackToSplit = nullptr;
  G4Step* fCopyInitStep = nullptr;
  G4String fProcessToSplit = "None";

  std::vector<G4Track> fTracksToPostpone;

  std::map<G4int, G4TrackVector> fRememberedTracks;
  std::map<G4int, std::vector<G4Step *>> fRememberedSteps;
  std::map<G4int, std::vector<G4String>> fRememberedProcesses;
  std::map<G4String,std::vector<G4String>> fListOfProcessesAccordingParticles;



  std::vector<std::string> fListOfVolumeAncestor;
  std::vector<std::string> fListOfBiasedVolume;

  std::vector<G4String> fListOfProcesses = {"compt", "annihil", "eBrem", "conv",
                                            "phot"};

  virtual void StartSimulationAction() override;
  virtual void SteppingAction(G4Step *) override;
  virtual void BeginOfEventAction(const G4Event *) override;
  virtual void EndOfEventAction(const G4Event *) override;
  virtual void BeginOfRunAction(const G4Run *run) override;
  virtual void PreUserTrackingAction(const G4Track *track) override;
  virtual void PostUserTrackingAction(const G4Track *track) override;

  // Pure splitting functions
  G4bool DoesParticleEmittedInSolidAngle(G4ThreeVector dir, G4ThreeVector vectorDirector, G4double maxTheta);
  G4Track *CreateComptonTrack(G4ParticleChangeForGamma *, G4Track, G4double);
  void ComptonSplitting(G4Step* initStep,G4Step *CurrentStep,G4VProcess *process,LastVertexDataContainer container);
  void SecondariesSplitting(G4Step* initStep, G4Step *CurrentStep,G4VProcess *process,LastVertexDataContainer container);

  void CreateNewParticleAtTheLastVertex(G4Step*init,G4Step *current, LastVertexDataContainer);
  G4Track* CreateATrackFromContainer(LastVertexDataContainer container, G4Step *step );
  G4bool IsTheParticleUndergoesAProcess(G4Step* step);
  G4VProcess* GetProcessFromProcessName(G4String particleName, G4String pName);
  G4VParticleChange* eBremProcessFinalState(G4Track* track, G4Step* step,G4VProcess *process);


  void FillOfDataTree(G4Step *step);
  G4bool IsParticleExitTheBiasedVolume(G4Step*step);
  void CreateListOfbiasedVolume(G4LogicalVolume *volume);
  void print_tree(const tree<LastVertexDataContainer>& tr, tree<LastVertexDataContainer>::pre_order_iterator it, tree<LastVertexDataContainer>::pre_order_iterator end);
};

#endif
