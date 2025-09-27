/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateKillParticlesNotCrossingMaterialsActor.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

GateKillParticlesNotCrossingMaterialsActor::
    GateKillParticlesNotCrossingMaterialsActor(py::dict &user_info)
    : GateVActor(user_info, true) {}

void GateKillParticlesNotCrossingMaterialsActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fMaterialsSparingParticles =
      DictGetVecStr(user_info, "material_sparing_particles");
}

void GateKillParticlesNotCrossingMaterialsActor::PreUserTrackingAction(
    const G4Track *track) {
  auto &l = fThreadLocalBooleanKilling.Get();
  l.fKillParticle = true;
}

void GateKillParticlesNotCrossingMaterialsActor::SteppingAction(G4Step *step) {
  G4Track *track = step->GetTrack();
  auto &l = fThreadLocalBooleanKilling.Get();
  // For the moment it also kills all secondaries potentially generated if the
  // mother track did not pass in one of the specified volume
  if (l.fKillParticle == true) {
    G4String materialName = track->GetMaterial()->GetName();
    if (std::find(fMaterialsSparingParticles.begin(),
                  fMaterialsSparingParticles.end(),
                  materialName) != fMaterialsSparingParticles.end()) {
      l.fKillParticle = false;
    }
  }
  if (l.fKillParticle == true) {
    G4String logicalVolumeNamePostStep = step->GetPostStepPoint()
                                             ->GetPhysicalVolume()
                                             ->GetLogicalVolume()
                                             ->GetName();
    if (step->GetPostStepPoint()->GetStepStatus() == 1) {
      if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),
                    logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()) {
        track->SetTrackStatus(fKillTrackAndSecondaries);
      }
    }
  }
}
