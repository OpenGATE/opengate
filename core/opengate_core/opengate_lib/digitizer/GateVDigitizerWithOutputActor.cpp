/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVDigitizerWithOutputActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiCollectionManager.h"
#include <iostream>

GateVDigitizerWithOutputActor::GateVDigitizerWithOutputActor(
    py::dict &user_info, bool MT_ready)
    : GateVActor(user_info, MT_ready) {

  // actions
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");

  // options for input
  fInputDigiCollectionName = DictGetStr(user_info, "input_digi_collection");

  // options for output
  fOutputFilename = DictGetStr(user_info, "output");
  fOutputDigiCollectionName = DictGetStr(user_info, "_name");
  fUserSkipDigiAttributeNames = DictGetVecStr(user_info, "skip_attributes");
  fClearEveryNEvents = DictGetInt(user_info, "clear_every");

  // init
  fOutputDigiCollection = nullptr;
  fInputDigiCollection = nullptr;
  fInitializeRootTupleForMasterFlag = true;
}

GateVDigitizerWithOutputActor::~GateVDigitizerWithOutputActor() = default;

void GateVDigitizerWithOutputActor::StartSimulationAction() {
  // Get the input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  fInputDigiCollection = hcm->GetDigiCollection(fInputDigiCollectionName);

  // Create the list of output attributes
  fOutputDigiCollection = hcm->NewDigiCollection(fOutputDigiCollectionName);
  fOutputDigiCollection->SetFilenameAndInitRoot(fOutputFilename);
  fOutputDigiCollection->InitDigiAttributesFromCopy(
      fInputDigiCollection, fUserSkipDigiAttributeNames);

  if (fInitializeRootTupleForMasterFlag)
    fOutputDigiCollection->RootInitializeTupleForMaster();
}

void GateVDigitizerWithOutputActor::BeginOfRunAction(const G4Run *run) {
  if (run->GetRunID() == 0)
    DigitInitializeNoParam();
}

void GateVDigitizerWithOutputActor::DigitInitializeNoParam() {
  std::vector<std::string> fake;
  DigitInitialize(fake);
}

void GateVDigitizerWithOutputActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  fOutputDigiCollection->RootInitializeTupleForWorker();

  // Init a Filler of all attributes except edep,
  // pos and time that will be set explicitly
  auto names = fOutputDigiCollection->GetDigiAttributeNames();
  for (auto &name : attributes_not_in_filler)
    names.erase(name);

  // Get thread local variables
  auto &l = fThreadLocalVDigitizerData.Get();

  // Create Filler of all remaining attributes (except the required ones)
  l.fDigiAttributeFiller = new GateDigiAttributesFiller(
      fInputDigiCollection, fOutputDigiCollection, names);

  // set input pointers to the attributes needed for computation
  l.fInputIter = fInputDigiCollection->NewIterator();
}

void GateVDigitizerWithOutputActor::BeginOfEventAction(const G4Event *event) {
  bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  fOutputDigiCollection->FillToRootIfNeeded(must_clear);
}

// Called every time a Run ends
void GateVDigitizerWithOutputActor::EndOfRunAction(const G4Run * /*unused*/) {
  fOutputDigiCollection->FillToRootIfNeeded(true);
  auto &iter = fThreadLocalVDigitizerData.Get().fInputIter;
  iter.Reset();
}

// Called every time a Run ends
void GateVDigitizerWithOutputActor::EndOfSimulationWorkerAction(
    const G4Run * /*unused*/) {
  fOutputDigiCollection->Write();
}

// Called when the simulation end
void GateVDigitizerWithOutputActor::EndSimulationAction() {
  fOutputDigiCollection->Write();
  fOutputDigiCollection->Close();
}
