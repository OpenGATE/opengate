/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "G4RunManager.hh"
#include "G4GeometryManager.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GateMotionVolumeActor.h"
#include "GateHelpersDict.h"

GateMotionVolumeActor::GateMotionVolumeActor(py::dict &user_info)
    : GateVActor(user_info, true) {
    fActions.insert("BeginOfRunAction");
    fTranslations = DictGetVecG4ThreeVector(user_info, "translations");
    fRotations = DictGetVecG4RotationMatrix(user_info, "rotations");
    fVolumeName = DictGetStr(user_info, "mother");
    // WARNING ! In G4VPlacement, the transform is build with the inverse of
    // the rotation matrix. To be consistent, we keep the inverse also here.
    for (auto &r: fRotations) {
        r.invert();
    }
}

GateMotionVolumeActor::~GateMotionVolumeActor() {
}


void GateMotionVolumeActor::PrepareRunToStartMasterAction(int run_id) {
    /*
       Open/Close geometry fails in multithread mode if not called by master
       In MultiThread : this function is called only by the master, by SourceManager
       In MonoThread  : this is called in the BeginOfRun (see below)
     */
    // get the physical volume
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto pv = pvs->GetVolume(fVolumeName);

    // open the geometry manager
    // https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomDynamic.html
    G4GeometryManager::GetInstance()->OpenGeometry(pv);

    // check the current rotation
    auto rot = pv->GetRotation();
    if (rot == nullptr) {
        // if no rotation has been given initially, the pointer is null, so we create one
        rot = new G4RotationMatrix();
        pv->SetRotation(rot);
    }

    // set translation
    auto t = fTranslations[run_id];
    pv->SetTranslation(t);

    // set rotation
    auto r = fRotations[run_id];//.inverse();
    rot->set(r.rep3x3());

    // close the geometry manager
    G4GeometryManager::GetInstance()->CloseGeometry(false, false, pv);
}

// Called every time a Run starts
void GateMotionVolumeActor::BeginOfRunAction(const G4Run *run) {
    if (!G4Threading::IsMultithreadedApplication()) {
        PrepareRunToStartMasterAction(run->GetRunID());
    }
}
