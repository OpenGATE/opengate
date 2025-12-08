/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePhaseSpaceActor.h"
#include "G4RunManager.hh"
#include "G4UnitsTable.hh"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiCollectionManager.h"
#include "digitizer/GateHelpersDigitizer.h"

G4Mutex TotalEntriesMutex = G4MUTEX_INITIALIZER;

GatePhaseSpaceActor::GatePhaseSpaceActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");
  fTotalNumberOfEntries = 0;
  fNumberOfAbsorbedEvents = 0;
  fStoreExitingStep = false;
  fStoreEnteringStep = false;
  fStoreFirstStepInVolume = false;
  fStoreAbsorbedEvent = false;
  fStoreAllSteps = false;
  fDebug = false;
}

GatePhaseSpaceActor::~GatePhaseSpaceActor() {
  // for debug
}

void GatePhaseSpaceActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fDigiCollectionName = DictGetStr(user_info, "name");
  fUserDigiAttributeNames = DictGetVecStr(user_info, "attributes");
  fStoreAbsorbedEvent = DictGetBool(user_info, "store_absorbed_event");
  fDebug = DictGetBool(user_info, "debug");

  // Special case to store event information even if the event does not step in
  // the mother volume
  if (fStoreAbsorbedEvent) {
    fActions.insert("EndOfEventAction");
  }
}

void GatePhaseSpaceActor::InitializeCpp() {
  fHits = nullptr;
  fTotalNumberOfEntries = 0;
  fNumberOfAbsorbedEvents = 0;
}

// Called when the simulation starts
void GatePhaseSpaceActor::StartSimulationAction() {
  fHits = GateDigiCollectionManager::GetInstance()->NewDigiCollection(
      fDigiCollectionName);

  std::string outputPath;
  if (!GetWriteToDisk(fOutputNameRoot)) {
    outputPath = "";
  } else {
    outputPath = GetOutputPath(fOutputNameRoot);
  }
  fHits->SetFilenameAndInitRoot(outputPath);
  fHits->InitDigiAttributesFromNames(fUserDigiAttributeNames);
  fHits->RootInitializeTupleForMaster();
  if (fStoreAbsorbedEvent) {
    CheckRequiredAttribute(fHits, "EventID");
    CheckRequiredAttribute(fHits, "EventPosition");
    CheckRequiredAttribute(fHits, "EventKineticEnergy");
    CheckRequiredAttribute(fHits, "EventDirection");
  }
  fNumberOfAbsorbedEvents = 0;
  fTotalNumberOfEntries = 0;
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
    // The current event still has to be stored
    l.fCurrentEventHasBeenStored = false;
  }
  if (fDebug) {
    auto id = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    std::cout << "New event " << id << std::endl;
  }
}

void GatePhaseSpaceActor::PreUserTrackingAction(const G4Track *track) {
  auto &l = fThreadLocalData.Get();
  l.fFirstStepInVolume = true;
  if (fDebug) {
    const auto id =
        G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    std::cout << "New track "
              << track->GetParticleDefinition()->GetParticleName()
              << track->GetTrackID() << " eid=" << id << std::endl;
  }
}

// Called every time a batch of steps must be processed
void GatePhaseSpaceActor::SteppingAction(G4Step *step) {
  /*
   Only store if the particle enters and/or exits the volume.
   (We CANNOT use step->IsFirstStepInVolume() because it fails with parallel
   world geometry) Warning: some particles can enter several times in the volume
   (backscatter), there will be two times in the phsp.

   When this function is triggered: we know the step is somewhere IN the volume.
   - Entering: pre step is at the boundary of the volume, so entering.
   - Exiting: post step is at the boundary of the volume (or the world if
   attached to the world)
   - FirstStepInVolume: this is the first time we see this particle in the
   volume (whatever is it at the boundary or not)
   */

  auto &l = fThreadLocalData.Get();

  // Particle enters the volume if the pre step is at the volume boundary
  const bool entering =
      step->GetPreStepPoint()->GetStepStatus() == fGeomBoundary;

  // Particle exits the volume if the post step is at the volume boundary or at
  // the world boundary if the phsp is attached to the world
  const bool exiting = IsStepExitingAttachedVolume(step);

  // When this is the first time we've seen this particle, fFirstStepInVolume is
  // true We then set it to false
  const bool first_step_in_volume = l.fFirstStepInVolume;
  l.fFirstStepInVolume = false;

  // Keep or ignore?
  bool ok = fStoreAllSteps;
  ok = ok || entering && fStoreEnteringStep;
  ok = ok || (exiting && fStoreExitingStep);
  ok = ok || (first_step_in_volume && fStoreFirstStepInVolume);
  if (!ok)
    return;

  // Fill the hits
  fHits->FillHits(step);

  // Set that at least one step for this event have been stored
  if (fStoreAbsorbedEvent) {
    l.fCurrentEventHasBeenStored = true;
  }

  // debug
  if (fDebug) {
    const auto s = fHits->DumpLastDigi();
    const auto id =
        G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    const auto *p = step->GetPreStepPoint()->GetProcessDefinedStep();
    const auto *vol = step->GetPreStepPoint()->GetTouchable()->GetVolume();
    const auto vol_name = vol->GetName();
    std::string pname = "noproc";
    if (p != nullptr)
      pname = p->GetProcessName();
    std::cout << GetName() << " "
              << step->GetTrack()->GetParticleDefinition()->GetParticleName()
              << /*" hits=" << fHits->GetSize() <<*/ " [" << entering << " "
              << exiting << " " << first_step_in_volume << "]"
              << " eid=" << id << " tid=" << step->GetTrack()->GetTrackID()
              << " vol=" << vol_name
              << " mat=" << vol->GetLogicalVolume()->GetMaterial()->GetName()
              << " pre="
              << G4BestUnit(step->GetPreStepPoint()->GetKineticEnergy(),
                            "Energy")
              << " step_n=" << step->GetTrack()->GetCurrentStepNumber()
              << " edep=" << G4BestUnit(step->GetTotalEnergyDeposit(), "Energy")
              << " proc=" << pname << " lastdigit=(" << s << ")" << std::endl;
  }
}

void GatePhaseSpaceActor::EndOfEventAction(const G4Event *event) {
  // For a given event, when no step never reaches the phsp:
  // if the option is on, we store a "fake" step, with the event information.
  // All other attributes will be "empty" (mostly 0)
  auto &l = fThreadLocalData.Get();
  if (fStoreAbsorbedEvent && !l.fCurrentEventHasBeenStored) {
    // Put empty value for all attributes
    fHits->FillDigiWithEmptyValue();

    // Except EventPosition
    auto *att = fHits->GetDigiAttribute("EventPosition");
    const auto p = event->GetPrimaryVertex(0)->GetPosition();
    auto &values = att->Get3Values();
    values.back() = p;

    // Except EventID
    att = fHits->GetDigiAttribute("EventID");
    auto &values_id = att->GetIValues();
    values_id.back() = event->GetEventID();

    // Except EventDirection
    att = fHits->GetDigiAttribute("EventDirection");
    auto &values_dir = att->Get3Values();
    const auto d =
        event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentumDirection();
    values_dir.back() = d;

    // Except EventKineticEnergy
    att = fHits->GetDigiAttribute("EventKineticEnergy");
    auto &values_en = att->GetDValues();
    const auto e =
        event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
    values_en.back() = e;

    // increase the number of absorbed events
    fNumberOfAbsorbedEvents++;
  }
}

// Called every time a Run ends
void GatePhaseSpaceActor::EndOfRunAction(const G4Run * /*unused*/) {
  {
    G4AutoLock mutex(&TotalEntriesMutex);
    fTotalNumberOfEntries += fHits->GetSize();
  }
  fHits->FillToRootIfNeeded(true);
}

// Called every time a Run ends
void GatePhaseSpaceActor::EndOfSimulationWorkerAction(
    const G4Run * /*unused*/) {
  fHits->Write();
}

// Called when the simulation ends
void GatePhaseSpaceActor::EndSimulationAction() {
  fHits->Write();
  fHits->Close();
}

int GatePhaseSpaceActor::GetNumberOfAbsorbedEvents() const {
  return fNumberOfAbsorbedEvents;
}

int GatePhaseSpaceActor::GetTotalNumberOfEntries() const {
  return fTotalNumberOfEntries;
}
