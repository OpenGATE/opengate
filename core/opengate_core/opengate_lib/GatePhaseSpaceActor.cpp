/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePhaseSpaceActor.h"
#include "G4RunManager.hh"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiCollectionManager.h"
#include "digitizer/GateHelpersDigitizer.h"

GatePhaseSpaceActor::GatePhaseSpaceActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");
  fOutputFilename = DictGetStr(user_info, "output");
  fDigiCollectionName = DictGetStr(user_info, "_name");
  fUserDigiAttributeNames = DictGetVecStr(user_info, "attributes");
  fStoreAbsorbedEvent = DictGetBool(user_info, "store_absorbed_event");
  fDebug = DictGetBool(user_info, "debug");
  fHits = nullptr;

  // Special case to store event information even if the event do not step in
  // the mother volume
  if (fStoreAbsorbedEvent) {
    fActions.insert("EndOfEventAction");
  }
}

GatePhaseSpaceActor::~GatePhaseSpaceActor() {
  // for debug
}

// Called when the simulation start
void GatePhaseSpaceActor::StartSimulationAction() {
  fHits = GateDigiCollectionManager::GetInstance()->NewDigiCollection(
      fDigiCollectionName);
  fHits->SetFilenameAndInitRoot(fOutputFilename);
  fHits->InitDigiAttributesFromNames(fUserDigiAttributeNames);
  fHits->RootInitializeTupleForMaster();
  if (fStoreAbsorbedEvent) {
    CheckRequiredAttribute(fHits, "EventID");
    CheckRequiredAttribute(fHits, "EventPosition");
    CheckRequiredAttribute(fHits, "EventKineticEnergy");
    CheckRequiredAttribute(fHits, "EventDirection");
    fNumberOfAbsorbedEvents = 0;
  }
}

// Called every time a Run starts
void GatePhaseSpaceActor::BeginOfRunAction(const G4Run *run) {
  if (run->GetRunID() == 0)
    fHits->RootInitializeTupleForWorker();
}

void GatePhaseSpaceActor::BeginOfEventAction(const G4Event * /*event*/) {
  auto &l = fThreadLocalData.Get();
  l.fFirstStepInVolume = true;
  if (fStoreAbsorbedEvent) {
    // The current event still have to be stored
    l.fCurrentEventHasBeenStored = false;
  }
}

void GatePhaseSpaceActor::PreUserTrackingAction(const G4Track *track) {
  auto &l = fThreadLocalData.Get();
  l.fFirstStepInVolume = true;
}

// Called every time a batch of step must be processed
void GatePhaseSpaceActor::SteppingAction(G4Step *step) {
  // Only store if this is the first time
  // Note we CANNOT use step->IsFirstStepInVolume() because it
  // fails with parallel world geometry
  auto &l = fThreadLocalData.Get();
  if (!l.fFirstStepInVolume)
    return;
  l.fFirstStepInVolume = false;
  // Fill the hits
  fHits->FillHits(step);
  // Set that at least one step for this event have been stored
  if (fStoreAbsorbedEvent) {
    l.fCurrentEventHasBeenStored = true;
  }
  if (fDebug) {
    auto s = fHits->DumpLastDigi();
    auto id = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    const auto *p = step->GetPreStepPoint()->GetProcessDefinedStep();
    auto *vol = step->GetPreStepPoint()->GetTouchable()->GetVolume();
    auto vol_name = vol->GetName();
    std::string pname = "none";
    if (p != nullptr)
      pname = p->GetProcessName();
    std::cout << GetName() << " eid=" << id
              << " tid=" << step->GetTrack()->GetTrackID() << " " << s
              << "  vol=" << vol_name
              << "  mat=" << vol->GetLogicalVolume()->GetMaterial()->GetName()
              << " proc=" << pname << std::endl;
  }
}

void GatePhaseSpaceActor::EndOfEventAction(const G4Event *event) {
  // For a given event, when no step never reach the phsp:
  // if the option is on, we store a "fake" step, with the event information.
  // All other attributes will be "empty" (mostly 0)
  auto &l = fThreadLocalData.Get();
  if (fStoreAbsorbedEvent && !l.fCurrentEventHasBeenStored) {
    // Put empty value for all attributes
    fHits->FillDigiWithEmptyValue();

    // Except EventPosition
    auto *att = fHits->GetDigiAttribute("EventPosition");
    auto p = event->GetPrimaryVertex(0)->GetPosition();
    auto &values = att->Get3Values();
    values.back() = p;

    // Except EventID
    att = fHits->GetDigiAttribute("EventID");
    auto &values_id = att->GetIValues();
    values_id.back() = event->GetEventID();

    // Except EventDirection
    att = fHits->GetDigiAttribute("EventDirection");
    auto &values_dir = att->Get3Values();
    auto d = event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentumDirection();
    values_dir.back() = d;

    // Except EventKineticEnergy
    att = fHits->GetDigiAttribute("EventKineticEnergy");
    auto &values_en = att->GetDValues();
    auto e = event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
    values_en.back() = e;

    // increase the nb of absorbed events
    fNumberOfAbsorbedEvents++;
  }
}

// Called every time a Run ends
void GatePhaseSpaceActor::EndOfRunAction(const G4Run * /*unused*/) {
  fHits->FillToRootIfNeeded(true);
}

// Called every time a Run ends
void GatePhaseSpaceActor::EndOfSimulationWorkerAction(
    const G4Run * /*unused*/) {
  fHits->Write();
}

// Called when the simulation end
void GatePhaseSpaceActor::EndSimulationAction() {
  fHits->Write();
  fHits->Close();
}
