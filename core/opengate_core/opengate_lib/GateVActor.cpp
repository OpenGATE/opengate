/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVActor.h"
#include "G4SDManager.hh"
#include "GateActorManager.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateMultiFunctionalDetector.h"

GateVActor::GateVActor(py::dict &user_info, bool MT_ready)
    : G4VPrimitiveScorer(DictGetStr(user_info, "_name")) {
  fMotherVolumeName = DictGetStr(user_info, "mother");
  // register this actor to the global list of actors
  GateActorManager::AddActor(this);
  // MT ?
  fMultiThreadReady = MT_ready;
  // Do not work (yet) with multi-thread
  if (!fMultiThreadReady && G4Threading::IsMultithreadedApplication()) {
    std::ostringstream oss;
    oss << "Sorry, the actor '" << GetName()
        << "' cannot (yet) be used in multi-threads mode. ";
    Fatal(oss.str());
  }
}

GateVActor::~GateVActor() {}

void GateVActor::AddActions(std::set<std::string> &actions) {
  fActions.insert(actions.begin(), actions.end());
}

void GateVActor::PreUserTrackingAction(const G4Track *track) {
  for (auto f : fFilters) {
    if (!f->Accept(track))
      return;
  }
}

void GateVActor::PostUserTrackingAction(const G4Track *track) {
  for (auto f : fFilters) {
    if (!f->Accept(track))
      return;
  }
}

G4bool GateVActor::ProcessHits(G4Step *step, G4TouchableHistory *) {
  /*
   In the G4 docs:

   "The second argument is a G4TouchableHistory object for the Readout geometry
   described in the next section. The second argument is NULL if Readout
   geometry is not assigned to this sensitive detector. In this method, one or
   more G4VHit objects should be constructed if the current step is meaningful
   for your detector."

   "The second argument of FillHits() method, i.e. G4TouchableHistory, is
   obsolete and not used. If user needs to define an artificial second geometry,
   use Parallel Geometries."

    => so we decide to simplify and remove "touchable" in the following.
   */

  for (auto f : fFilters) {
    // we only perform the SteppingAction if ALL filters are true
    // If only one is false, we stop and return.
    if (!f->Accept(step))
      return true;
  }
  SteppingAction(step);
  return true;
}

void GateVActor::RegisterSD(G4LogicalVolume *lv) {
  // Look is a SD already exist for this LV
  auto currentSD = lv->GetSensitiveDetector();
  GateMultiFunctionalDetector *mfd;
  if (!currentSD) {
    // This is the first time a SD is set to this LV
    auto f = new GateMultiFunctionalDetector("mfd_" + lv->GetName());
    G4SDManager::GetSDMpointer()->AddNewDetector(f);
    lv->SetSensitiveDetector(f);
    mfd = f;
  } else {
    // A SD already exist, we reused it
    mfd = dynamic_cast<GateMultiFunctionalDetector *>(currentSD);
    for (auto i = 0; i < mfd->GetNumberOfPrimitives(); i++) {
      if (mfd->GetPrimitive(i)->GetName() == GetName()) {
        // In that case the actor is already registered, we skip to avoid
        // G4 exception. It happens when the LogVol has several PhysVol
        // (repeater)
        return;
      }
    }
  }
  // Register the actor to the GateMultiFunctionalDetector
  mfd->RegisterPrimitive(this);
}
