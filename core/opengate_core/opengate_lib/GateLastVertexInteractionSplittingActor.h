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

#include "GateVActor.h"
#include "G4ParticleChangeForGamma.hh"
#include "G4VEnergyLossProcess.hh"
#include <iostream>
#include <pybind11/stl.h>
namespace py = pybind11;



class GateLastVertexInteractionSplittingActor : public GateVActor {
public:
  GateLastVertexInteractionSplittingActor(py::dict &user_info);
  virtual ~GateLastVertexInteractionSplittingActor() {}

  G4double fSplittingFactor;
  G4bool fRussianRouletteForAngle = false;
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
  G4bool fIsSplitted = false;

  G4Track* fTrackToSplit = nullptr;
  G4Step* fStepToSplit = nullptr;
  G4String fProcessToSplit = "None";

  std::vector<G4Track> fTracksToPostpone;
  
  std::map<G4int,G4TrackVector> fRememberedTracks;
  std::map<G4int,std::vector<G4Step*>> fRememberedSteps;
  std::map<G4int,std::vector<G4String>> fRememberedProcesses;

  std::vector<std::string> fListOfVolumeAncestor;

  std::vector<G4String> fListOfProcesses = {"compt","annihil","eBrem","conv","phot"}; 

  virtual void SteppingAction(G4Step *) override;
  virtual void BeginOfEventAction(const G4Event *) override;
  virtual void BeginOfRunAction(const G4Run *run) override;
  virtual void PreUserTrackingAction(const G4Track* track) override;
  virtual void PostUserTrackingAction(const G4Track* track) override;

  //Pure splitting functions
  G4double RussianRouletteForAngleSurvival(G4ThreeVector, G4ThreeVector, G4double, G4double);
  G4Track* CreateComptonTrack(G4ParticleChangeForGamma*,G4Track, G4double);
  void ComptonSplitting(G4Step* CurrentStep,G4Track* track,const G4Step* step,G4VProcess* process);
  void SecondariesSplitting(G4Step* CurrentStep,G4Track* track,const G4Step* step,G4VProcess* process);


  //Handling the remembered processes to replay
  void RememberLastProcessInformation(G4Step*);
  void CreateNewParticleAtTheLastVertex(G4Step*,G4Track*,const G4Step*,G4String);
  void ResetProcessesForEnteringParticles(G4Step * step);
  void ClearRememberedTracksAndSteps(std::map<G4int, G4TrackVector>, std::map<G4int, std::vector<G4Step *>>);


  //Edge case to handle the bias in annihilation
  //FIXME : The triple annihilation is not handled for the moment
  void PostponeFirstAnnihilationTrackIfInteraction(G4Step *step,G4String processName);
  void RegenerationOfPostponedAnnihilationTrack(G4Step *step);
  void HandleTrackIDIfPostponedAnnihilation(G4Step* step);
  
  

};

#endif
