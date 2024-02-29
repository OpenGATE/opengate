/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateLETActor.h"
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
G4Mutex SetLETPixelMutex = G4MUTEX_INITIALIZER;

GateLETActor::GateLETActor(py::dict &user_info) : GateVActor(user_info, true) {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_numerator_image = ImageType::New();
  cpp_denominator_image = ImageType::New();
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("EndSimulationAction");
  // Option: compute uncertainty
  fdoseAverage = DictGetBool(user_info, "dose_average");
  ftrackAverage = DictGetBool(user_info, "track_average");
  fLETtoOtherMaterial = DictGetBool(user_info, "let_to_other_material");
  fotherMaterial = DictGetStr(user_info, "other_material");
  // fQAverage = DictGetBool(user_info, "qAverage");
  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateLETActor::ActorInitialize() {}

void GateLETActor::BeginOfRunAction(const G4Run *) {
  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<ImageType>(cpp_numerator_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  AttachImageToVolume<ImageType>(cpp_denominator_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  // compute volume of a dose voxel
  auto sp = cpp_numerator_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
  static G4Material *water =
      G4NistManager::Instance()->FindOrBuildMaterial(fotherMaterial);
}

void GateLETActor::SteppingAction(G4Step *step) {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

  // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?

  // consider random position between pre and post
  auto position = postGlobal;
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
  ImageType::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  // get pixel index
  ImageType::IndexType index;
  bool isInside =
      cpp_numerator_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {
    // With mutex (thread)
    G4AutoLock mutex(&SetLETPixelMutex);

    // get edep in MeV (take weight into account)
    auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
    double dedx_cut = DBL_MAX;
    // dedx
    auto *current_material = step->GetPreStepPoint()->GetMaterial();
    auto density = current_material->GetDensity() / CLHEP::g * CLHEP::cm3;
    // double dedx_currstep = 0., dedx_water = 0.;
    // double density_water = 1.0;
    //  other material
    const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();

    auto energy1 = step->GetPreStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    auto energy2 = step->GetPostStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    auto energy = (energy1 + energy2) / 2;
    // Accounting for particles with dedx=0; i.e. gamma and neutrons
    // For gamma we consider the dedx of electrons instead - testing
    // with 1.3 MeV photon beam or 150 MeV protons or 1500 MeV carbon ion
    // beam showed that the error induced is 0 		when comparing
    // dose and dosetowater in the material G4_WATER For neutrons the dose
    // is neglected - testing with 1.3 MeV photon beam or 150 MeV protons or
    // 1500 MeV carbon ion beam showed that the error induced is < 0.01%
    //		when comparing dose and dosetowater in the material
    // G4_WATER (we are systematically missing a little bit of dose of
    // course with this solution)

    if (p == G4Gamma::Gamma())
      p = G4Electron::Electron();
    auto &l = fThreadLocalData.Get().emcalc;
    auto dedx_currstep =
        l.ComputeElectronicDEDX(energy, p, current_material, dedx_cut) /
        CLHEP::MeV * CLHEP::mm;

    auto steplength = step->GetStepLength() / CLHEP::mm;
    double scor_val_num = 0.;
    double scor_val_den = 0.;

    if (fLETtoOtherMaterial) {
      auto density_water = water->GetDensity() / CLHEP::g * CLHEP::cm3;
      auto dedx_water = l.ComputeElectronicDEDX(energy, p, water, dedx_cut) /
                        CLHEP::MeV * CLHEP::mm;
      auto SPR_otherMaterial = dedx_water / dedx_currstep;
      edep *= SPR_otherMaterial;
      dedx_currstep *= SPR_otherMaterial;
    }

    if (fdoseAverage) {
      scor_val_num = edep * dedx_currstep / CLHEP::MeV / CLHEP::MeV * CLHEP::mm;
      scor_val_den = edep / CLHEP::MeV;
    } else if (ftrackAverage) {
      scor_val_num = steplength * dedx_currstep * w / CLHEP::MeV;
      scor_val_den = steplength * w / CLHEP::mm;
    }
    ImageAddValue<ImageType>(cpp_numerator_image, index, scor_val_num);
    ImageAddValue<ImageType>(cpp_denominator_image, index, scor_val_den);
    //}

  } // else : outside the image
}

void GateLETActor::EndSimulationAction() {}
