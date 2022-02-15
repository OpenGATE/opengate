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
#include "GamDictHelpers.h"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;

GamDoseActor::GamDoseActor(py::dict &user_info)
    : GamVActor(user_info) {
    // Create the image pointer
    // (the size and allocation will be performed on the py side)
    cpp_edep_image = ImageType::New();
    // Action for this actor: during stepping
    fActions.insert("SteppingAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndSimulationAction");
    // Option: compute uncertainty
    fUncertaintyFlag = DictBool(user_info, "uncertainty");
    fVolumeName = DictStr(user_info, "mother");
    fInitialTranslation = Dict3DVector(user_info, "translation");
}

void GamDoseActor::ActorInitialize() {
    if (fUncertaintyFlag) {
        cpp_square_image = ImageType::New();
        cpp_temp_image = ImageType::New();
        cpp_last_id_image = ImageType::New();
    }
}

void GamDoseActor::BeginOfRunAction(const G4Run *run) {
    // Important ! The volume may have moved, so we re-attach each run
    AttachImageToVolume<ImageType>(cpp_edep_image, fVolumeName, fInitialTranslation);
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
    // auto position = postGlobal;
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
    bool isInside = cpp_edep_image->TransformPhysicalPointToIndex(point, index);

    // set value
    if (isInside) {
        // With mutex (thread)
        G4AutoLock mutex(&SetPixelMutex);

        // If uncertainty: consider edep per event
        if (fUncertaintyFlag) {
            auto event_id = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
            auto previous_id = cpp_last_id_image->GetPixel(index);
            cpp_last_id_image->SetPixel(index, event_id);
            if (event_id == previous_id) {
                // Same event : continue temporary edep
                ImageAddValue<ImageType>(cpp_temp_image, index, edep);
            } else {
                // Different event : update previous and start new event
                auto e = cpp_temp_image->GetPixel(index);
                ImageAddValue<ImageType>(cpp_edep_image, index, e);
                ImageAddValue<ImageType>(cpp_square_image, index, e * e);
                // new temp value
                cpp_temp_image->SetPixel(index, edep);
            }
        } else {
            ImageAddValue<ImageType>(cpp_edep_image, index, edep);
        }
    } // else : outside the image
}

void GamDoseActor::EndSimulationAction() {
}
