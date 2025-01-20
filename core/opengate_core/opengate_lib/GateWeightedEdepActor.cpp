/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateWeightedEdepActor.h"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "G4Deuteron.hh"
#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4Positron.hh"
#include "G4Proton.hh"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetWeightedPixelMutex = G4MUTEX_INITIALIZER;
G4Mutex SetWeightedPixelBetaMutex = G4MUTEX_INITIALIZER;
G4Mutex SetWeightedNbEventMutex = G4MUTEX_INITIALIZER;

GateWeightedEdepActor::GateWeightedEdepActor(py::dict &user_info) : GateVActor(user_info, true) {
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("EndSimulationAction");
}

void GateWeightedEdepActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);

  fScoreIn = DictGetStr(user_info, "score_in");
  if (fScoreIn != "material") {
    fScoreInOtherMaterial = true;
  }

  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateWeightedEdepActor::InitializeCpp() {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_numerator_image = Image3DType::New();
  cpp_denominator_image = Image3DType::New();
  if (multipleScoring){
  std::cout<<"Creating second numerator"<<std::endl;
    cpp_second_numerator_image = Image3DType::New();
  }
}

void GateWeightedEdepActor::BeginOfRunActionMasterThread(int run_id) {
  // Reset the number of events (per run)
  NbOfEvent = 0;

  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<Image3DType>(cpp_numerator_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  AttachImageToVolume<Image3DType>(cpp_denominator_image, fPhysicalVolumeName,
                                 fInitialTranslation);
                                 
  if (multipleScoring){
  std::cout<<"Initializing second numerator"<<std::endl;
    AttachImageToVolume<Image3DType>(cpp_second_numerator_image, fPhysicalVolumeName,
                                       fInitialTranslation);
  }
  // compute volume of a dose voxel
  auto sp = cpp_numerator_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
}

void GateWeightedEdepActor::BeginOfRunAction(const G4Run *) {
  if (fScoreInOtherMaterial) {
    auto &l = fThreadLocalData.Get();
    l.materialToScoreIn =
        G4NistManager::Instance()->FindOrBuildMaterial(fScoreIn);
  }
}

void GateWeightedEdepActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetWeightedNbEventMutex);
  NbOfEvent++;
}

G4double GateWeightedEdepActor::CalcMeanEnergy(G4Step *step){
    // get edep in MeV (take weight into account)
    auto energy1 = step->GetPreStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    auto energy2 = step->GetPostStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    G4double energy = (energy1 + energy2) / 2;
    
    return energy;

}

G4double GateWeightedEdepActor::GetSPROtherMaterial(G4Step *step, G4double energy){
    double dedx_cut = DBL_MAX;
    auto &l = fThreadLocalData.Get();
    const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();
     if (p == G4Gamma::Gamma()) {
       p = G4Electron::Electron();
     }
     
    auto *current_material = step->GetPreStepPoint()->GetMaterial(); 
    auto dedx_currstep =
        l.emcalc.ComputeElectronicDEDX(energy, p, current_material, dedx_cut) /
        CLHEP::MeV * CLHEP::mm;

    auto dedx_other_material = l.emcalc.ComputeElectronicDEDX(
                                   energy, p, l.materialToScoreIn, dedx_cut) /
                               CLHEP::MeV * CLHEP::mm;
    G4double SPR_otherMaterial = dedx_other_material / dedx_currstep;
    
    return SPR_otherMaterial;

}

double GateWeightedEdepActor::ScoringQuantityFn(G4Step *step, double *secondQuantity){
// the primary scoring quantity is calculated in the function and returned
// if a second scoring quantity is necessary, one can pass a pointer to a custom variable
// the variable is then assigned the value for the second scoring quantity
   return 1.0;
   }
   
void GateWeightedEdepActor::GetVoxelPosition(G4Step *step, G4ThreeVector &position,
                                     bool &isInside,
                                     Image3DType::IndexType &index) const {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

  // consider random position between pre and post
  if (fHitType == "pre") {
    position = preGlobal;
  }
  if (fHitType == "random") {
    auto x = G4UniformRand();
    auto direction = postGlobal - preGlobal;
    position = preGlobal + x * direction;
  }
  if (fHitType == "middle") {
    auto direction = postGlobal - preGlobal;
    position = preGlobal + 0.5 * direction;
  }

  auto localPosition =
      touchable->GetHistory()->GetTransform(0).TransformPoint(position);

  // convert G4ThreeVector to itk PointType
  Image3DType::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  isInside = cpp_numerator_image->TransformPhysicalPointToIndex(point, index);
}

void GateWeightedEdepActor::SteppingAction(G4Step *step) {

  // Get the voxel index
  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, isInside, index);
  G4double averagingQuantity;
  
  // if inside the voxel, add avereging quantity to the denominator image
  // and add weighted avereging quantityto the numerator image
  if (isInside) {
    auto w = step->GetTrack()->GetWeight();
    if (doTrackAverage){
    averagingQuantity = step->GetStepLength() / CLHEP::mm * w;
      }
    else {
      averagingQuantity = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
    }
    
    double secondQuantity = 1.0;
    auto scoringQuantity = ScoringQuantityFn(step, &secondQuantity);
    
    {
      std::cout<<"adding value to alpha image"<<std::endl;
      G4AutoLock mutex(&SetWeightedPixelMutex);
      ImageAddValue<Image3DType>(cpp_numerator_image, index, averagingQuantity*scoringQuantity);
      ImageAddValue<Image3DType>(cpp_denominator_image, index, averagingQuantity);
    }
    if (multipleScoring){
        std::cout<<"adding value to beta image"<<std::endl;
        std::cout<<"second scoring quantity: "<<secondQuantity<<std::endl;
        {
          G4AutoLock mutex(&SetWeightedPixelBetaMutex);
          ImageAddValue<Image3DType>(cpp_second_numerator_image, index, averagingQuantity*secondQuantity);
        }
          std::cout<<"value added to image image"<<std::endl;
    }
  } // else : outside the image
}


void GateWeightedEdepActor::EndSimulationAction() {}
