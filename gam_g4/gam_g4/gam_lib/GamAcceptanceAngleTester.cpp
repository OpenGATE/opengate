/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4Navigator.hh"
#include "GamAcceptanceAngleTester.h"
#include "GamHelpersImage.h"
#include "GamHelpersDict.h"

GamAcceptanceAngleTester::GamAcceptanceAngleTester(std::string volume,
                                                   bool vIntersectionFlag,
                                                   bool vNormalFlag,
                                                   double vNormalAngleTolerance,
                                                   G4ThreeVector vNormalVector) {
    fAcceptanceAngleVolumeName = volume;
    fAASolid = nullptr;
    fAASkippedParticles = 0;
    fAALastRunId = -1;
    fAANavigator = nullptr;
    fAAPhysicalVolume = nullptr;

    DDD(fAcceptanceAngleVolumeName);
    // Retrieve the solid
    auto lvs = G4LogicalVolumeStore::GetInstance();
    auto lv = lvs->GetVolume(fAcceptanceAngleVolumeName);
    fAASolid = lv->GetSolid();

    // Retrieve the physical volume
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    fAAPhysicalVolume = pvs->GetVolume(fAcceptanceAngleVolumeName);

    // Init a navigator that will be used to find the transform
    auto world = pvs->GetVolume("world");
    fAANavigator = new G4Navigator();
    fAANavigator->SetWorldVolume(world);

    // parameters
    DDD("here");
    //DDD(param);
    /*auto angle_acceptance_intersection_flag = DictBool(user_info, "angle_acceptance_intersection_flag");
   auto angle_acceptance_normal_flag = DictBool(user_info, "angle_acceptance_normal_flag");
   auto angle_acceptance_normal_vector = Dict3DVector(user_info, "angle_acceptance_normal_vector");
   auto angle_acceptance_normal_tolerance = DictBool(user_info, "angle_acceptance_normal_tolerance");
   auto volumes = DictVecStr(user_info, "angle_acceptance_volumes");
   fSPS->SetAcceptanceAngleVolumes(volumes);*/
    fIntersectionFlag = vIntersectionFlag;
    fNormalFlag = vNormalFlag;
    fNormalAngleTolerance = vNormalAngleTolerance;
    fNormalVector = vNormalVector;
}

void GamAcceptanceAngleTester::UpdateTransform() {
    // Get the transformation
    G4ThreeVector tr;
    fAARotation = new G4RotationMatrix;
    ComputeTransformationFromWorldToVolume(fAcceptanceAngleVolumeName, tr, *fAARotation);
    // It is not fully clear why the AffineTransform need the inverse
    fAATransform = G4AffineTransform(fAARotation->inverse(), tr);
}

bool GamAcceptanceAngleTester::TestIfAccept(G4ThreeVector &position, G4ThreeVector &momentum_direction) {
    auto localPosition = fAATransform.TransformPoint(position);
    auto localDirection = (*fAARotation) * (momentum_direction);
    if (fIntersectionFlag) {
        auto dist = fAASolid->DistanceToIn(localPosition, localDirection);
        if (dist == kInfinity) return false;
    }
    if (fNormalFlag) {
        auto angle = fNormalVector.angle(localDirection);
        if (angle > fNormalAngleTolerance) return false;
    }
    return true;
}
