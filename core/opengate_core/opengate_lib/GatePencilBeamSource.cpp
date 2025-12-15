/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePencilBeamSource.h"
#include "G4IonTable.hh"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GatePencilBeamSource::GatePencilBeamSource() : GateGenericSource() {}

GatePencilBeamSource::~GatePencilBeamSource() = default;

GatePencilBeamSource::threadLocalPencilBeamSource &
GatePencilBeamSource::GetThreadLocalDataPencilBeamSource() {
  return fThreadLocalDataPencilBeamSource.Get();
}

void GatePencilBeamSource::CreateSPS() {
  auto &lll = GetThreadLocalDataPencilBeamSource();
  lll.fSPS_PB = new GateSingleParticleSourcePencilBeam(std::string(),
                                                       fAttachedToVolumeName);
  auto &ll = GetThreadLocalDataGenericSource();
  ll.fSPS = lll.fSPS_PB;
}

void GatePencilBeamSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto &l = fThreadLocalData.Get();
  auto &lll = GetThreadLocalDataPencilBeamSource();
  lll.fSPS_PB->SetSourceRotTransl(l.fGlobalTranslation, l.fGlobalRotation);
}

void GatePencilBeamSource::InitializeDirection(py::dict puser_info) {
  // GateGenericSource::InitializeDirection(puser_info);
  //  PBS parameters
  auto dir_info = py::dict(puser_info["direction"]);
  auto x_param = DictGetVecDouble(dir_info, "partPhSp_x");
  auto y_param = DictGetVecDouble(dir_info, "partPhSp_y");
  auto &lll = GetThreadLocalDataPencilBeamSource();
  lll.fSPS_PB->SetPBSourceParam(x_param, y_param);

  // angle acceptance ?
  auto d = py::dict(puser_info["direction"]);
  auto dd = DictToMap(d["angular_acceptance"]);
  auto &l = fThreadLocalDataGenericSource.Get();
  l.fAAManager = new GateAcceptanceAngleManager;
  l.fAAManager->Initialize(dd, false);
  if (l.fAAManager->IsEnabled()) {
    Fatal("Sorry, cannot use Acceptance Angle with Pencil Beam source (yet).");
  }
}
