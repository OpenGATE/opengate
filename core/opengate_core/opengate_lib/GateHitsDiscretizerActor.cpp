/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitsDiscretizerActor.h"
#include "G4PhysicalVolumeStore.hh"
#include "GateHelpersDict.h"
#include "GateHitsCollectionManager.h"
#include <iostream>

GateHitsDiscretizerActor::GateHitsDiscretizerActor(py::dict &user_info)
    : GateVActor(user_info, true) {

  // actions
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");

  // options
  fOutputFilename = DictGetStr(user_info, "output");
  fOutputHitsCollectionName = DictGetStr(user_info, "_name");
  fInputHitsCollectionName = DictGetStr(user_info, "input_hits_collection");
  fClearEveryNEvents = DictGetInt(user_info, "clear_every");

  // init
  fOutputHitsCollection = nullptr;
  fInputHitsCollection = nullptr;
}

GateHitsDiscretizerActor::~GateHitsDiscretizerActor() = default;

void GateHitsDiscretizerActor::SetVolumeDepth(int depth_x, int depth_y,
                                              int depth_z) {
  fDepthX = depth_x;
  fDepthY = depth_y;
  fDepthZ = depth_z;
}

// Called when the simulation start
void GateHitsDiscretizerActor::StartSimulationAction() {
  // Get the input hits collection
  auto *hcm = GateHitsCollectionManager::GetInstance();
  fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
  CheckRequiredAttribute(fInputHitsCollection, "PostPosition");

  // Create the list of output attributes
  auto names = fInputHitsCollection->GetHitAttributeNames();

  // Create the output hits collection with the same list of attributes
  fOutputHitsCollection = hcm->NewHitsCollection(fOutputHitsCollectionName);
  fOutputHitsCollection->SetFilename(fOutputFilename);
  fOutputHitsCollection->InitializeHitAttributes(names);
  fOutputHitsCollection->InitializeRootTupleForMaster();
}

// Called every time a Run starts
void GateHitsDiscretizerActor::BeginOfRunAction(const G4Run *run) {
  if (run->GetRunID() == 0)
    InitializeComputation();
}

void GateHitsDiscretizerActor::InitializeComputation() {
  fOutputHitsCollection->InitializeRootTupleForWorker();

  // Init a Filler of all attributes except pos that will be set explicitly
  auto names = fOutputHitsCollection->GetHitAttributeNames();
  names.erase("PostPosition");

  // Get thread local variables
  auto &l = fThreadLocalData.Get();

  // Create Filler of all remaining attributes (except the required ones)
  l.fHitsAttributeFiller = new GateHitsAttributesFiller(
      fInputHitsCollection, fOutputHitsCollection, names);

  // set output pointers to the attributes needed for computation
  fOutputPosAttribute = fOutputHitsCollection->GetHitAttribute("PostPosition");

  // set input pointers to the attributes needed for computation
  l.fInputIter = fInputHitsCollection->NewIterator();
  l.fInputIter.TrackAttribute("PostPosition", &l.pos);
  l.fInputIter.TrackAttribute("PreStepUniqueVolumeID", &l.volID);

  // FIXME
  // pre compute all discrete positions -> python ?
}

void GateHitsDiscretizerActor::BeginOfEventAction(const G4Event *event) {
  bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  fOutputHitsCollection->FillToRootIfNeeded(must_clear);
}

void GateHitsDiscretizerActor::EndOfEventAction(const G4Event * /*unused*/) {
  // loop on all hits
  auto &l = fThreadLocalData.Get();
  auto &iter = l.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    // consider post position and change to the center of the volume
    // FIXME

    auto vid = l.volID->get();
    G4ThreeVector res;
    G4ThreeVector cx = G4ThreeVector(); // 0,0,0 = center of a volume
    G4ThreeVector cy = G4ThreeVector(); // 0,0,0 = center of a volume
    G4ThreeVector cz = G4ThreeVector(); // 0,0,0 = center of a volume
    auto tx = vid->GetLocalToWorldTransform(fDepthX);
    auto ty = vid->GetLocalToWorldTransform(fDepthY);
    auto tz = vid->GetLocalToWorldTransform(fDepthZ);
    tx->ApplyPointTransform(cx);
    ty->ApplyPointTransform(cy);
    tz->ApplyPointTransform(cz);
    res.set(cx.getX(), cy.getY(), cz.getZ());
    fOutputPosAttribute->Fill3Value(res);

    /*t = vid->GetWorldToLocalTransform(5);

    tr = G4ThreeVector(*l.pos);
    c = G4ThreeVector();
    t->ApplyPointTransform(tr);
    DDD(tr);
    t->ApplyPointTransform(c);
    DDD(c);*/

    // fOutputPosAttribute->Fill3Value(c);
    // fOutputPosAttribute->Fill3Value(*l.pos);

    // copy all other attributes for this hit
    l.fHitsAttributeFiller->Fill(iter.fIndex);
    iter++;
  }
}

// Called every time a Run ends
void GateHitsDiscretizerActor::EndOfRunAction(const G4Run * /*unused*/) {
  fOutputHitsCollection->FillToRootIfNeeded(true);
  auto &iter = fThreadLocalData.Get().fInputIter;
  iter.Reset();
}

// Called every time a Run ends
void GateHitsDiscretizerActor::EndOfSimulationWorkerAction(
    const G4Run * /*unused*/) {
  fOutputHitsCollection->Write();
}

// Called when the simulation end
void GateHitsDiscretizerActor::EndSimulationAction() {
  fOutputHitsCollection->Write();
  fOutputHitsCollection->Close();
}
