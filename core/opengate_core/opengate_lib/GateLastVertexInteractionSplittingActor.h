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

#include "GateAcceptanceAngleManager.h"
#include "GateLastVertexSource.h"
#include "GateLastVertexSplittingDataContainer.h"
#include "GateVActor.h"
#include <CLHEP/Vector/ThreeVector.h>
#include <G4ParticleChangeForGamma.hh>
#include <G4StackManager.hh>
#include <G4VEnergyLossProcess.hh>
#include <pybind11/stl.h>
#include <tree/tree.hh>

using CLHEP::Hep3Vector;

namespace py = pybind11;

class GateLastVertexInteractionSplittingActor : public GateVActor {
public:
  GateLastVertexInteractionSplittingActor(py::dict &user_info);
  virtual ~GateLastVertexInteractionSplittingActor() {}

  // Configuration is set before transport and shared read-only by workers.
  G4double fSplittingFactor;
  G4bool fOnlyTree = false;
  G4double fBatchSize;
  G4int fNbOfMaxBatchPerEvent;
  std::vector<std::string> fListOfVolumeAncestor;
  std::map<std::string, std::string> fAcceptanceAngleParameters;

  // One state per actor and worker. No locks in tracking/stepping callbacks.
  struct WorkerState {
    GateAcceptanceAngleManager *fAAManager = nullptr;
    G4int fEventID = 0;
    G4int fTrackID = 0;
    G4double fEkin = 0;
    G4bool fIsFirstStep = true;
    G4double fSplitCounter = 0;
    G4bool fToSplit = true;
    const GateVSource *fActiveSource = nullptr;
    G4bool fIsAnnihilAlreadySplit = false;
    G4bool fKilledBecauseOfProcess = false;
    G4bool fAbortedEvent = false;
    G4double fWeight = 0;
    G4int fNumberOfTrackToSimulate = 0;
    G4int fNbOfBatchForExitingParticle = 0;
    GateLastVertexSource *fVertexSource = nullptr;
    tree<LastVertexDataContainer> fTree;
    tree<LastVertexDataContainer>::post_order_iterator fIterator;
    std::vector<LastVertexDataContainer> fListOfContainer;
    G4StackManager *fStackManager = nullptr;
    long fRemovedParticle = 0;
    long fNumberOfReplayedParticle = 0;
    long fNumberOfReplayedEvent = 0;
    long fNumberOfEvent = 0;
    G4Track *fTrackToSplit = nullptr;
    G4Step *fCopyInitStep = nullptr;
    G4String fProcessNameToSplit;
    G4VProcess *fProcessToSplit = nullptr;
    LastVertexDataContainer fContainer;
    GateSourceManager *fSourceManager = nullptr;
    WorkerState() = default;
    WorkerState(const WorkerState &) = delete;
    WorkerState &operator=(const WorkerState &) = delete;
    ~WorkerState();
    void ReleaseResources();
  };
  G4Cache<WorkerState> fWorkerState;

  // Reduced only once per worker, after its last run.
  long fRemovedParticle = 0;
  long fNumberOfReplayedParticle = 0;
  long fNumberOfReplayedEvent = 0;
  long fNumberOfEvent = 0;

  void InitializeUserInfo(py::dict &user_info) override;
  void StartSimulationAction() override;
  void EndOfSimulationWorkerAction(const G4Run *) override;
  virtual void SteppingAction(G4Step *) override;
  virtual void BeginOfEventAction(const G4Event *) override;
  virtual void EndOfEventAction(const G4Event *) override;
  virtual void BeginOfRunAction(const G4Run *run) override;
  virtual void PreUserTrackingAction(const G4Track *track) override;

  // Pure splitting functions
  void InitializeAAManager(const std::map<std::string, std::string> &user_info);
  G4Track *CreateComptonTrack(G4ParticleChangeForGamma *, G4Track, G4double);
  void ComptonSplitting(G4Step *initStep, G4VProcess *process,
                        G4double batchSize);
  void SecondariesSplitting(G4Step *initStep, G4VProcess *process,
                            LastVertexDataContainer container,
                            G4double batchSize);

  void CreateNewParticleAtTheLastVertex(G4Step *init, LastVertexDataContainer,
                                        G4double batchSize);
  G4Track *CreateATrackFromContainer(LastVertexDataContainer container);
  G4bool IsTheParticleUndergoesALossEnergyProcess(G4Step *step);
  G4VProcess *GetProcessFromProcessName(G4String particleName, G4String pName);
  G4Track eBremProcessFinalState(G4Track *track, G4Step *step);

  void FillOfDataTree(G4Step *step);
  G4bool IsParticleExitTheBiasedVolume(G4Step *step);
  inline long GetNumberOfKilledParticles() { return fRemovedParticle; }
  inline long GetNumberOfReplayedEvents() { return fNumberOfReplayedEvent; }
  inline long GetNumberOfEvents() { return fNumberOfEvent; }
  inline long GetNumberOfReplayedParticles() {
    return fNumberOfReplayedParticle;
  }
};

#endif
