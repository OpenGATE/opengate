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
#include "GamDictHelpers.h"

GamMotionVolumeActor::GamMotionVolumeActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fTranslations = DictVec3DVector(user_info, "translations");
    fRotations = DictVecRotation(user_info, "rotations");
    // WARNING ! In G4VPlacement, the transform is build with the inverse of
    // the rotation matrix. To be consistent, we keep the inverse also here.
    for (auto &r: fRotations) {
        r.invert();
    }
}

GamMotionVolumeActor::~GamMotionVolumeActor() {
}

// Called when the simulation start
void GamMotionVolumeActor::StartSimulationAction() {
    DDD("GamMotionVolumeActor::StartSimulationAction");
}

// Called every time a Run starts
void GamMotionVolumeActor::BeginOfRunAction(const G4Run *run) {
    DDD("");
    DDD("GamMotionVolumeActor::BeginOfRunAction");
    DDD(run->GetRunID());
    // get the physical volume
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto pv = pvs->GetVolume("spect"); // FIXME parameter
    // open the geometry manager
    G4GeometryManager::GetInstance()->OpenGeometry(pv);
    // change position
    auto t = fTranslations[run->GetRunID()];
    DDD(pv->GetTranslation());
    DDD(t);
    pv->SetTranslation(t);
    DDD(pv->GetTranslation());
    auto rot = pv->GetRotation();
    DDD(rot);
    if (rot == nullptr) {
        G4RotationMatrix *r = new G4RotationMatrix();
        pv->SetRotation(r);
    }
    DDD(*pv->GetRotation());
    auto r = fRotations[run->GetRunID()];//.inverse();
    DDD(r);
    rot->set(r.rep3x3());
    DDD(*pv->GetRotation());
    // close the geometry manager
    G4GeometryManager::GetInstance()->CloseGeometry(pv);
    DDD("End of geom change)")
}


// Called every time a Run ends
void GamMotionVolumeActor::EndOfRunAction(const G4Run *run) {
    DDD("end of run");

}

void GamMotionVolumeActor::EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) {

}

// Called when the simulation end
void GamMotionVolumeActor::EndSimulationAction() {

}

