/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateMotionVolumeActor.h"
#include "G4GeometryManager.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4RunManager.hh"
#include "GateHelpersDict.h"
#include <iostream>

G4Mutex GeometryChangeMutex = G4MUTEX_INITIALIZER;

GateMotionVolumeActor::GateMotionVolumeActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  // fActions.insert("BeginOfRunAction");
}

GateMotionVolumeActor::~GateMotionVolumeActor() {}

void GateMotionVolumeActor::SetTranslations(std::vector<G4ThreeVector> &t) {
  fTranslations = t;
}

void GateMotionVolumeActor::SetRotations(std::vector<G4RotationMatrix> &rot) {
  fRotations = rot;
  // WARNING ! In G4VPlacement, the transform is build with the inverse of
  // the rotation matrix. To be consistent, we keep the inverse also here.
  for (auto &r : fRotations) {
    r.invert();
  }
}

void GateMotionVolumeActor::MoveGeometry(int run_id) {
  // Open/Close geometry MUST only be called in the master thread
  // get the physical volume
  auto pvs = G4PhysicalVolumeStore::GetInstance();
  auto pv = pvs->GetVolume(fMotherVolumeName);

  // open the geometry manager
  // https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomDynamic.html
  auto *gm = G4GeometryManager::GetInstance();
  gm->OpenGeometry(pv);

  // check the current rotation
  auto rot = pv->GetRotation();
  if (rot == nullptr) {
    // if no rotation has been given initially, the pointer is null, so we
    // create one
    rot = new G4RotationMatrix();
    pv->SetRotation(rot);
  }

  // set translation
  auto t = fTranslations[run_id];
  pv->SetTranslation(t);

  // set rotation
  auto r = fRotations[run_id]; //.inverse();
  rot->set(r.rep3x3());

  // close the geometry manager
  gm->CloseGeometry(false, false, pv);
  // G4RunManager::GetRunManager()->GeometryHasBeenModified(true);
}

// Called every time a Run starts
/*void GateMotionVolumeActor::BeginOfRunAction(const G4Run *run) {
}*/

void GateMotionVolumeActor::BeginOfRunActionMasterThread(int run_id) {
  MoveGeometry(run_id);
}
