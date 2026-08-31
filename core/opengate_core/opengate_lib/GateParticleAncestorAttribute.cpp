/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateParticleAncestorAttribute.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"
#include <G4StepPoint.hh>
#include <G4VPhysicalVolume.hh>
#include <G4VProcess.hh>
#include <limits>

GateParticleAncestorAttribute::GateParticleAncestorAttribute(
    py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fActions.insert("SteppingAction");
  fActions.insert("PreUserTrackingAction");
}

void GateParticleAncestorAttribute::InitializeUserInfo(py::dict &user_info) {
  GateVAuxiliaryAttribute::InitializeUserInfo(user_info);
  fAttributeToStore = DictGetStr(user_info, "value_to_store");
  fParticleName = DictGetStr(user_info, "particle_name");
  if (fAttributeToStore == "VertexPosition") {
    fDigiAttributeType = '3';
  } else if (fAttributeToStore == "VertexKineticEnergy") {
    fDigiAttributeType = 'D';
  } else {
    fDigiAttributeType = '3';
  }
}

void GateParticleAncestorAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();
  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    if (fDigiAttributeType == '3') {
      att->Fill3Value(Get3Value(step));
    } else if (fDigiAttributeType == 'D') {
      att->FillDValue(GetDValue(step));
    }
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

G4ThreeVector
GateParticleAncestorAttribute::Get3Value(const G4Step *step) const {
  // Use NaN when not set
  const auto nan = std::numeric_limits<double>::quiet_NaN();
  return GetStoredTrackDataValue<GateThreeVectorTrackData, G4ThreeVector>(
      step, G4ThreeVector(nan, nan, nan));
}

double GateParticleAncestorAttribute::GetDValue(const G4Step *step) const {
  // Use NaN when not set
  const auto nan = std::numeric_limits<double>::quiet_NaN();
  return GetStoredTrackDataValue<GateDoubleTrackData, double>(step, nan);
}

void GateParticleAncestorAttribute::SteppingAction(const G4Step *step) {
  // propagate the gamma ancestor to secondaries
  if (fDigiAttributeType == '3') {
    PropagateTrackDataToSecondariesInCurrentStep<GateThreeVectorTrackData>(
        step);
  } else if (fDigiAttributeType == 'D') {
    PropagateTrackDataToSecondariesInCurrentStep<GateDoubleTrackData>(step);
  }
}

void GateParticleAncestorAttribute::PreUserTrackingAction(
    const G4Track *track) {
  // Check if a UserTrackInfo already exist, if yes, do nothing.
  if (fDigiAttributeType == '3') {
    if (GetTrackData<GateThreeVectorTrackData>(track) != nullptr) {
      return;
    }
  } else if (fDigiAttributeType == 'D') {
    if (GetTrackData<GateDoubleTrackData>(track) != nullptr) {
      return;
    }
  }

  // if this is a new gamma (and the first one), store the value
  if (track->GetParticleDefinition()->GetParticleName() == fParticleName) {
    if (fDigiAttributeType == '3') {
      SetStoredTrackDataValue<GateThreeVectorTrackData, G4ThreeVector>(
          track, track->GetVertexPosition());
    }
    if (fDigiAttributeType == 'D') {
      SetStoredTrackDataValue<GateDoubleTrackData, double>(
          track, track->GetVertexKineticEnergy());
    }
  }
}
