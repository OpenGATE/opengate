/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePencilBeamSource.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GatePencilBeamSource::GatePencilBeamSource() : GateGenericSource() {
  fSPS_PB = nullptr;
}

GatePencilBeamSource::~GatePencilBeamSource() = default;

void GatePencilBeamSource::CreateSPS() {
  fSPS_PB = new GateSingleParticleSourcePencilBeam(std::string(),
                                                   fAttachedToVolumeName);
  fSPS = fSPS_PB;
}

void GatePencilBeamSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  fSPS_PB->SetSourceRotTransl(fGlobalTranslation, fGlobalRotation);
}

void GatePencilBeamSource::InitializeDirection(py::dict puser_info) {
  // GateGenericSource::InitializeDirection(puser_info);
  //  PBS parameters
  auto dir_info = py::dict(puser_info["direction"]);
  auto x_param = DictGetVecDouble(dir_info, "partPhSp_x");
  auto y_param = DictGetVecDouble(dir_info, "partPhSp_y");
  fSPS_PB->SetPBSourceParam(x_param, y_param);

  // angle acceptance ?
  auto d = py::dict(puser_info["direction"]);
  auto dd = DictToMap(d["angular_acceptance"]);
  fAAManager = new GateAcceptanceAngleManager;
  fAAManager->Initialize(dd, false);
  if (fAAManager->IsEnabled()) {
    Fatal("Sorry, cannot use Acceptance Angle with Pencil Beam source (yet).");
  }
}
