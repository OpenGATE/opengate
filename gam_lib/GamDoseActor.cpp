/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4RandomTools.hh"
#include "G4Navigator.hh"
#include "G4RunManager.hh"
#include "GamDoseActor.h"
#include "GamImageHelpers.h"
#include "GamHelpers.h"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;

GamDoseActor::GamDoseActor(py::dict &user_info)
    : GamVActor(user_info) {
    // Create the image pointer
    // The size and allocation will be performed on the py side
    cpp_image = ImageType::New();
    // Action for this actor: during stepping
    fActions.insert("SteppingAction");
    fActions.insert("EndSimulationAction");

    fUncertaintyFlag = true; // FIXME

}

void GamDoseActor::ActorInitialize() {
    DDD("ActorInitialize");
    if (fUncertaintyFlag) {
        cpp_square_image = ImageType::New();
        cpp_temp_image = ImageType::New();
        cpp_last_id_image = ImageType::New();
        cpp_uncertainty_image = ImageType::New();
    }
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
        if (fUncertaintyFlag) {
            // if (sameEvent) mEdepImage.AddTempValue(index, edep);
            //          else mEdepImage.AddValueAndUpdate(index, edep);
            auto event_id = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
            DDD(event_id);
            DDD(index);
            auto previous_id = cpp_last_id_image->GetPixel(index);
            DDD(previous_id);
            cpp_last_id_image->SetPixel(index, event_id);
            if (event_id == previous_id) { // AddTempValue
                DDD("same event");
                ImageAddValue<ImageType>(cpp_temp_image, index, edep);
                /*
                edep += cpp_temp_image->GetPixel(index);
                cpp_temp_image->SetPixel(index, edep);
                 */
            } else { // AddValueAndUpdate
                DDD("diff event");
                // get previous edep and set it + squared
                auto e = cpp_temp_image->GetPixel(index);
                DDD(e);
                ImageAddValue<ImageType>(cpp_image, index, e);
                ImageAddValue<ImageType>(cpp_square_image, index, e * e);
                // new temp value
                DDD(edep);
                cpp_temp_image->SetPixel(index, edep);
            }
        } else {
            ImageAddValue<ImageType>(cpp_image, index, edep);
            /*
            edep += cpp_image->GetPixel(index); // FIXME maybe 2 x FastComputeOffset can be spared
            cpp_image->SetPixel(index, edep);*/
        }

    } // else : outside the image
}
