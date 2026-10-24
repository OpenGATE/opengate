#include "GateVoxelWTSource.h"
#include "GateSPSVoxelsPosDistribution.h"
#include "GateWindowTurboSource.h"

GateVoxelWTSource::GateVoxelWTSource() : GateWindowTurboSource() {
  fVoxelPositionGenerator = new GateSPSVoxelsPosDistribution();
}

void GateVoxelWTSource::PrepareNextRun() {
  GateWindowTurboSource::PrepareNextRun();

  fVoxelPositionGenerator->fGlobalRotation = fGlobalRotation;
  fVoxelPositionGenerator->fGlobalTranslation = fGlobalTranslation;
}

void GateVoxelWTSource::InitializePosition(py::dict) {
  fSPS->SetPosGenerator(fVoxelPositionGenerator);
  fVoxelPositionGenerator->SetPosDisType("Point");
}
