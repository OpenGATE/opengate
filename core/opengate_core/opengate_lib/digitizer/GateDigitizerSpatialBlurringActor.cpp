/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerSpatialBlurringActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersGeometry.h"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <G4Navigator.hh>
#include <G4VoxelLimits.hh>
#include <Randomize.hh>
#include <iostream>

GateDigitizerSpatialBlurringActor::GateDigitizerSpatialBlurringActor(
    py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {

  // actions
  fActions.insert("EndOfEventAction");

  // blurring method
  fBlurAttributeName = DictGetStr(user_info, "blur_attribute");
  fBlurSigma3 = DictGetG4ThreeVector(user_info, "blur_sigma");
  fKeepInSolidLimits = DictGetBool(user_info, "keep_in_solid_limits");
}

GateDigitizerSpatialBlurringActor::~GateDigitizerSpatialBlurringActor() =
    default;

void GateDigitizerSpatialBlurringActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  auto a = attributes_not_in_filler;
  a.push_back(fBlurAttributeName);
  GateVDigitizerWithOutputActor::DigitInitialize(a);

  CheckRequiredAttribute(fInputDigiCollection, "PostStepUniqueVolumeID");

  // set output pointers to the attributes needed for computation
  fOutputBlurAttribute =
      fOutputDigiCollection->GetDigiAttribute(fBlurAttributeName);

  // set input pointers to the attributes needed for computation
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  lr.fInputIter.TrackAttribute(fBlurAttributeName, &l.fAtt3Value);
  lr.fInputIter.TrackAttribute("PostStepUniqueVolumeID", &l.fVolumeId);
}

void GateDigitizerSpatialBlurringActor::BeginOfRunAction(const G4Run *run) {
  GateVDigitizerWithOutputActor::BeginOfRunAction(run);
  G4ThreeVector translation;
  G4RotationMatrix rotation;
  ComputeTransformationFromWorldToVolume(fMotherVolumeName, translation,
                                         rotation);
  fWorldToVolume = G4AffineTransform(rotation.inverse(), translation);

  ComputeTransformationFromVolumeToWorld(fMotherVolumeName, translation,
                                         rotation, true);
  fVolumeToWorld = G4AffineTransform(rotation.inverse(), translation);

  if (run->GetRunID() == 0) {
    // Init a navigator that will be used to find the transform
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto world = pvs->GetVolume("world");
    auto &l = fThreadLocalData.Get();
    l.fNavigator = new G4Navigator();
    l.fNavigator->SetWorldVolume(world);
  }
}

void GateDigitizerSpatialBlurringActor::EndOfEventAction(
    const G4Event * /*unused*/) {
  // loop on all digi of this events
  // auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &iter = lr.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    // blur the current value
    BlurCurrentThreeVectorValue();
    // copy the other attributes
    auto &i = lr.fInputIter.fIndex;
    lr.fDigiAttributeFiller->Fill(i);
    iter++;
  }
}

void GateDigitizerSpatialBlurringActor::BlurCurrentThreeVectorValue() {
  // Get the current position
  auto &l = fThreadLocalData.Get();
  auto &vec = *l.fAtt3Value;

  // locate to find the volume that contains the point
  G4VPhysicalVolume *phys_vol;
  if (fKeepInSolidLimits) {
    G4TouchableHistory fTouchableHistory;
    l.fNavigator->LocateGlobalPointAndUpdateTouchable(vec, &fTouchableHistory);
    auto vid = GateUniqueVolumeID::New(&fTouchableHistory);
    phys_vol = vid->GetVolumeDepthID().back().fVolume;
  }

  // consider local position
  auto v = fWorldToVolume.TransformPoint(vec);
  G4ThreeVector p(G4RandGauss::shoot(v.getX(), fBlurSigma3.getX()),
                  G4RandGauss::shoot(v.getY(), fBlurSigma3.getY()),
                  G4RandGauss::shoot(v.getZ(), fBlurSigma3.getZ()));

  if (fKeepInSolidLimits) {
    // check limits according to the volume
    G4VoxelLimits limits;
    G4double Xmin, Xmax, Ymin, Ymax, Zmin, Zmax;
    G4AffineTransform at;

    auto solid = phys_vol->GetLogicalVolume()->GetSolid();
    solid->CalculateExtent(kXAxis, limits, at, Xmin, Xmax);
    solid->CalculateExtent(kYAxis, limits, at, Ymin, Ymax);
    solid->CalculateExtent(kZAxis, limits, at, Zmin, Zmax);

    static const double tiny = 1 * CLHEP::nm;

    if (p.getX() < Xmin)
      p.setX(Xmin + tiny);
    if (p.getY() < Ymin)
      p.setY(Ymin + tiny);
    if (p.getZ() < Zmin)
      p.setZ(Zmin + tiny);

    if (p.getX() > Xmax)
      p.setX(Xmax - tiny);
    if (p.getY() > Ymax)
      p.setY(Ymax - tiny);
    if (p.getZ() > Zmax)
      p.setZ(Zmax - tiny);
  }

  // convert back to global position
  p = fVolumeToWorld.TransformPoint(p);

  // store
  fOutputBlurAttribute->Fill3Value(p);
}
