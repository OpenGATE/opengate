/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4RandomTools.hh"
#include "G4Navigator.hh"

#include "GamDoseActor.h"
#include "GamHelpers.h"

G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;


GamDoseActor::GamDoseActor(py::dict &user_info) : GamVActor(user_info) {
    // Create the image pointer
    // The size and allocation will be performed on the py side
    cpp_image = ImageType::New();
    // Action for this actor: during stepping
    fActions.push_back("SteppingAction");
}


void GamDoseActor::SteppingAction(G4Step *step, G4TouchableHistory *) {
    auto preGlobal = step->GetPreStepPoint()->GetPosition();
    auto postGlobal = step->GetPostStepPoint()->GetPosition();
    auto touchable = step->GetPreStepPoint()->GetTouchable();
    // auto depth = touchable->GetHistoryDepth();
    // Depth = 0 bottom level
    // Depth = 1 mother
    // Depth = 2 grand mother

    // If the volume has multiple copy, touchable->GetCopyNumber(0)
    // send the copy number

    // random position along the step
    auto x = G4UniformRand();
    auto direction = postGlobal - preGlobal;
    auto position = preGlobal + x * direction;
    auto localPosition = touchable->GetHistory()->GetTransform(0).TransformPoint(position);

    // convert G4ThreeVector to itk PointType
    point[0] = localPosition[0];
    point[1] = localPosition[1];
    point[2] = localPosition[2];

    // set image pixel
    // FIXME hit middle/random etc
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV;
    cpp_image->TransformPhysicalPointToIndex(point, index);
    /*std::cout << "depth=" << depth
              << " x " << x << std::endl
              << "tr0 " << touchable->GetHistory()->GetTransform(0).NetTranslation()
              << "tr1 " << touchable->GetHistory()->GetTransform(1).NetTranslation()
              << "tr2 " << touchable->GetHistory()->GetTransform(2).NetTranslation()
              << std::endl
              << " spac " << cpp_image->GetSpacing()
              << " pG " << preGlobal
              << " p " << localPosition
              << " -> " << index << std::endl;
              */
    if (cpp_image->GetLargestPossibleRegion().IsInside(index)) {
        // With mutex (thread)
        G4AutoLock mutex(&SetPixelMutex);
        edep += cpp_image->GetPixel(index);
        cpp_image->SetPixel(index, edep);
        mutex.unlock();
    } // else : outside the image
}
