#include "GateVoxelWTSource.h"
#include "GateSPSVoxelsPosDistribution.h"
#include "GateWindowTurboSource.h"

GateVoxelWTSource::GateVoxelWTSource() : GateWindowTurboSource() {
  fVoxelPositionGenerator = new GateSPSVoxelsPosDistribution();
}

void GateVoxelWTSource::PrepareNextRun() {
  GateWindowTurboSource::PrepareNextRun();

  auto &l = GetThreadLocalData();
  fGlobalRotation = l.fGlobalRotation;
  fVoxelPositionGenerator->fGlobalTranslation = l.fGlobalTranslation;
}

void GateVoxelWTSource::InitializePosition(py::dict) {
  fSPS->SetPosGenerator(fVoxelPositionGenerator);
  fVoxelPositionGenerator->SetPosDisType("Point");
}
