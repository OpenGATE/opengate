/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVoxelSource.h"

GateVoxelSource::GateVoxelSource() : GateGenericSource() {
  fVoxelPositionGenerator = new GateSPSVoxelsPosDistribution();
}

GateVoxelSource::~GateVoxelSource() = default;

void GateVoxelSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto *pos = fSPS->GetPosDist();
  pos->SetCentreCoords(fGlobalTranslation);

  // orientation according to mother volume
  const auto rotation = fGlobalRotation;
  G4ThreeVector r1(rotation(0, 0), rotation(1, 0), rotation(2, 0));
  G4ThreeVector r2(rotation(0, 1), rotation(1, 1), rotation(2, 1));
  pos->SetPosRot1(r1);
  pos->SetPosRot2(r2);

  fVoxelPositionGenerator->fGlobalRotation = fGlobalRotation;
  fVoxelPositionGenerator->fGlobalTranslation = fGlobalTranslation;
  // the direction is 'isotropic' so we don't care about rotating the direction.
}

void GateVoxelSource::InitializePosition(py::dict) {
  fSPS->SetPosGenerator(fVoxelPositionGenerator);
  // we set a fake value (not used)
  fVoxelPositionGenerator->SetPosDisType("Point");
}
