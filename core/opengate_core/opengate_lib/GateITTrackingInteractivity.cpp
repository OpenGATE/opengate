/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateITTrackingInteractivity.h"

GateITTrackingInteractivity::GateITTrackingInteractivity()
    : G4ITTrackingInteractivity() {}

void GateITTrackingInteractivity::RegisterActor(GateVChemistryActor *actor) {
  if (actor->HasAction("InitializeChemistryTracking")) {
    fInitializeTrackingActors.push_back(actor);
  }
  if (actor->HasAction("AppendChemistryStep")) {
    fAppendStepActors.push_back(actor);
  }
  if (actor->HasAction("StartChemistryTracking")) {
    fStartTrackingActors.push_back(actor);
  }
  if (actor->HasAction("EndChemistryTracking")) {
    fEndTrackingActors.push_back(actor);
  }
  if (actor->HasAction("FinalizeChemistryTracking")) {
    fFinalizeTrackingActors.push_back(actor);
  }
}

void GateITTrackingInteractivity::Initialize() {
  for (auto actor : fInitializeTrackingActors) {
    actor->InitializeChemistryTracking();
  }
}

void GateITTrackingInteractivity::AppendStep(G4Track *track, G4Step *step) {
  for (auto actor : fAppendStepActors) {
    actor->AppendChemistryStep(track, step);
  }
}

void GateITTrackingInteractivity::StartTracking(G4Track *track) {
  for (auto actor : fStartTrackingActors) {
    actor->StartChemistryTracking(track);
  }
}

void GateITTrackingInteractivity::EndTracking(G4Track *track) {
  for (auto actor : fEndTrackingActors) {
    actor->EndChemistryTracking(track);
  }
}

void GateITTrackingInteractivity::Finalize() {
  for (auto actor : fFinalizeTrackingActors) {
    actor->FinalizeChemistryTracking();
  }
}
