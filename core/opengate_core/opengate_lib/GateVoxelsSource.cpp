/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVoxelsSource.h"
#include "G4ParticleTable.hh"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"

GateVoxelsSource::GateVoxelsSource() : GateGenericSource() {
  fVoxelPositionGenerator = new GateSPSVoxelsPosDistribution();
}

GateVoxelsSource::~GateVoxelsSource() {}

void GateVoxelsSource::PrepareNextRun() {
  // GateGenericSource::PrepareNextRun();
  //  rotation and translation to apply, according to mother volume
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto &l = fThreadLocalData.Get();
  auto *pos = fSPS->GetPosDist();
  pos->SetCentreCoords(l.fGlobalTranslation);

  // orientation according to mother volume
  auto rotation = l.fGlobalRotation;
  G4ThreeVector r1(rotation(0, 0), rotation(1, 0), rotation(2, 0));
  G4ThreeVector r2(rotation(0, 1), rotation(1, 1), rotation(2, 1));
  pos->SetPosRot1(r1);
  pos->SetPosRot2(r2);

  // auto &l = fThreadLocalData.Get();
  fVoxelPositionGenerator->fGlobalRotation = l.fGlobalRotation;
  fVoxelPositionGenerator->fGlobalTranslation = l.fGlobalTranslation;
  // the direction is 'isotropic' so we don't care about rotating the direction.
}

void GateVoxelsSource::InitializePosition(py::dict) {
  fSPS->SetPosGenerator(fVoxelPositionGenerator);
  // we set a fake value (not used)
  fVoxelPositionGenerator->SetPosDisType("Point");
}
