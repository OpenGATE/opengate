/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVoxelizedPromptGammaTLESource.h"
#include "G4ParticleTable.hh"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"

GateVoxelizedPromptGammaTLESource::GateVoxelizedPromptGammaTLESource()
    : GateGenericSource() {
  fVoxelPositionGenerator = new GateSPSVoxelsPosDistribution();
  std::cout << "construct GateVoxelizedPromptGammaTLESource" << std::endl;
}

GateVoxelizedPromptGammaTLESource::~GateVoxelizedPromptGammaTLESource() =
    default;

void GateVoxelizedPromptGammaTLESource::PrepareNextRun() {
  std::cout << "GateVoxelizedPromptGammaTLESource::PrepareNextRun" << std::endl;
  // GateGenericSource::PrepareNextRun();
  //  rotation and translation to apply, according to mother volume
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto *pos = fSPS->GetPosDist();
  pos->SetCentreCoords(fGlobalTranslation);

  // orientation according to mother volume
  auto rotation = fGlobalRotation;
  G4ThreeVector r1(rotation(0, 0), rotation(1, 0), rotation(2, 0));
  G4ThreeVector r2(rotation(0, 1), rotation(1, 1), rotation(2, 1));
  pos->SetPosRot1(r1);
  pos->SetPosRot2(r2);

  fVoxelPositionGenerator->fGlobalRotation = fGlobalRotation;
  fVoxelPositionGenerator->fGlobalTranslation = fGlobalTranslation;
  // the direction is 'isotropic' so we don't care about rotating the direction.
}

void GateVoxelizedPromptGammaTLESource::InitializePosition(py::dict) {
  fSPS->SetPosGenerator(fVoxelPositionGenerator);
  // we set a fake value (not used)
  fVoxelPositionGenerator->SetPosDisType("Point");
}
