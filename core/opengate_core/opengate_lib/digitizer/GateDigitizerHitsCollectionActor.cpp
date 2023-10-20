/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerHitsCollectionActor.h"
#include "../GateHelpersDict.h"
#include "G4RunManager.hh"
#include "GateDigiCollectionManager.h"

GateDigitizerHitsCollectionActor::GateDigitizerHitsCollectionActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  // actions
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");
  // options
  fOutputFilename = DictGetStr(user_info, "output");
  fHitsCollectionName = DictGetStr(user_info, "_name");
  fUserDigiAttributeNames = DictGetVecStr(user_info, "attributes");
  fDebug = DictGetBool(user_info, "debug");
  fClearEveryNEvents = DictGetInt(user_info, "clear_every");
  fKeepZeroEdep = DictGetBool(user_info, "keep_zero_edep");
  // init
  fHits = nullptr;
}

GateDigitizerHitsCollectionActor::~GateDigitizerHitsCollectionActor() {}

// Called when the simulation start
void GateDigitizerHitsCollectionActor::StartSimulationAction() {
  auto *dcm = GateDigiCollectionManager::GetInstance();
  fHits = dcm->NewDigiCollection(fHitsCollectionName);
  // This order is important: filename and attributes must be set before Root
  // initialization
  fHits->SetFilenameAndInitRoot(fOutputFilename);
  fHits->InitDigiAttributesFromNames(fUserDigiAttributeNames);
  fHits->RootInitializeTupleForMaster();
}

// Called every time a Run starts
void GateDigitizerHitsCollectionActor::BeginOfRunAction(const G4Run *run) {
  // Needed to create the root output (only the first run)
  if (run->GetRunID() == 0)
    fHits->RootInitializeTupleForWorker();
}

void GateDigitizerHitsCollectionActor::BeginOfEventAction(
    const G4Event *event) {
  /*
     FillToRootIfNeeded is *required* at the beginning of the event because it
     calls SetBeginOfEventIndex.
     The list of hits is cleared every 'fClearEveryNEvents'.
     There is (almost) no time penalty whatever this value, it only impacts
     memory (lower is better). Default fClearEveryNEvents value is 1. Some other
     actors may need hits from several events, so we leave the option to keep
     more events. It only fills to root if needed.
   */
  bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  fHits->FillToRootIfNeeded(must_clear);
}

// Called every time a batch of step must be processed
void GateDigitizerHitsCollectionActor::SteppingAction(G4Step *step) {
  // Do not store step with zero edep
  if (fKeepZeroEdep || step->GetTotalEnergyDeposit() > 0)
    fHits->FillHits(step);
  if (fDebug) {
    // nb edep = 0
    auto s = fHits->DumpLastDigi();
    auto id = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    std::string x =
        step->GetTotalEnergyDeposit() > 0 ? "" : " (not stored edep=0) ";
    std::cout << GetName() << " " << id << x << " " << s << std::endl;
    // nb transportation
    auto post = step->GetPostStepPoint();
    auto process = post->GetProcessDefinedStep();
    auto pname = process->GetProcessName();
    static int nb_tr = 0;
    if (pname == "Transportation") {
      nb_tr++;
      std::cout << pname << " " << nb_tr << " " << id << x << std::endl;
    }
  }
}

// Called every time a Run ends
void GateDigitizerHitsCollectionActor::EndOfRunAction(const G4Run * /*run*/) {
  /*
   * We consider flushing values every run.
   * If a process need to access hits across different run, this should be move
   * in EndOfSimulationWorkerAction.
   */
  fHits->FillToRootIfNeeded(true);
}

void GateDigitizerHitsCollectionActor::EndOfSimulationWorkerAction(
    const G4Run * /*lastRun*/) {
  // Write only once per worker thread
  fHits->Write();
}

// Called when the simulation end
void GateDigitizerHitsCollectionActor::EndSimulationAction() {
  fHits->Write();
  fHits->Close();
}
