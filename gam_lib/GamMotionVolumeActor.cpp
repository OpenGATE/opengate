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
#include "GamMotionVolumeActor.h"
#include "GamHelpersDict.h"

GamMotionVolumeActor::GamMotionVolumeActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("BeginOfRunAction");
    fTranslations = DictVec3DVector(user_info, "translations");
    fRotations = DictVecRotation(user_info, "rotations");
    fVolumeName = DictStr(user_info, "mother");
    // WARNING ! In G4VPlacement, the transform is build with the inverse of
    // the rotation matrix. To be consistent, we keep the inverse also here.
    for (auto &r: fRotations) {
        r.invert();
    }
}

GamMotionVolumeActor::~GamMotionVolumeActor() {
}

// Called every time a Run starts
void GamMotionVolumeActor::BeginOfRunAction(const G4Run *run) {
    // get the physical volume
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto pv = pvs->GetVolume(fVolumeName);

    // open the geometry manager
    G4GeometryManager::GetInstance()->OpenGeometry(pv);

    // check the current rotation
    auto rot = pv->GetRotation();
    if (rot == nullptr) {
        // if no rotation has been given initially, the pointer is null, so we create one
        rot = new G4RotationMatrix();
        pv->SetRotation(rot);
    }

    // set translation
    auto t = fTranslations[run->GetRunID()];
    pv->SetTranslation(t);

    // set rotation
    auto r = fRotations[run->GetRunID()];//.inverse();
    rot->set(r.rep3x3());

    // close the geometry manager
    G4GeometryManager::GetInstance()->CloseGeometry(pv);
}
