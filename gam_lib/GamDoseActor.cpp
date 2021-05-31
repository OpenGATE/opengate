/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4RandomTools.hh"
#include "G4Navigator.hh"
#include "GamDoseActor.h"
#include "GamHelpers.h"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;

GamDoseActor::GamDoseActor(py::dict &user_info) : GamVActor(user_info) {
    // Create the image pointer
    // The size and allocation will be performed on the py side
    cpp_image = ImageType::New();
    // Action for this actor: during stepping
    fActions.push_back("SteppingAction");
    fActions.push_back("EndSimulationAction");
}

void GamDoseActor::EndSimulationAction() {
}

void GamDoseActor::SteppingAction(G4Step *step, G4TouchableHistory *) {
    auto preGlobal = step->GetPreStepPoint()->GetPosition();
    auto postGlobal = step->GetPostStepPoint()->GetPosition();
    auto touchable = step->GetPreStepPoint()->GetTouchable();

    // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?

    // consider random position between pre and post
    auto x = G4UniformRand();
    auto direction = postGlobal - preGlobal;
    auto position = preGlobal + x * direction;
    auto localPosition = touchable->GetHistory()->GetTransform(0).TransformPoint(position);

    // convert G4ThreeVector to itk PointType
    ImageType::PointType point;
    point[0] = localPosition[0];
    point[1] = localPosition[1];
    point[2] = localPosition[2];

    // get edep in MeV (take weight into account)
    auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;

    // get pixel index
    ImageType::IndexType index;
    bool isInside = cpp_image->TransformPhysicalPointToIndex(point, index);

    // set value
    if (isInside) {
        // With mutex (thread)
        G4AutoLock mutex(&SetPixelMutex);
        edep += cpp_image->GetPixel(index); // FIXME maybe 2 x FastComputeOffset can be spared
        cpp_image->SetPixel(index, edep);
    } // else : outside the image
}
