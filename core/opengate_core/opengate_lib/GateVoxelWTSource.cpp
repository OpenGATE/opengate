#include "GateVoxelWTSource.h"
#include "GateSPSVoxelsPosDistribution.h"
#include "GateWindowTurboSource.h"

GateVoxelWTSource::GateVoxelWTSource() : GateWindowTurboSource() {
  fVoxelPositionGenerator = new GateSPSVoxelsPosDistribution();
}

void GateVoxelWTSource::PrepareNextRun() {
  GateWindowTurboSource::PrepareNextRun();

  auto &l = GetThreadLocalData();
  fVoxelPositionGenerator->fGlobalRotation = l.fGlobalRotation;
  fVoxelPositionGenerator->fGlobalTranslation = l.fGlobalTranslation;
}

void GateVoxelWTSource::InitializePosition(py::dict) {
  auto &ll = GetThreadLocalDataGenericSource();
  ll.fSPS->SetPosGenerator(fVoxelPositionGenerator);
  fVoxelPositionGenerator->SetPosDisType("Point");
}
