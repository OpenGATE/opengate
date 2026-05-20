#include "GateVoxelWTSource.h"
#include "GateSPSVoxelsPosDistribution.h"
#include "GateWindowTurboSource.h"

GateVoxelWTSource::GateVoxelWTSource() : GateWindowTurboSource() {
  fVoxelPositionGenerator.Get() = new GateSPSVoxelsPosDistribution();
}

void GateVoxelWTSource::PrepareNextRun() {
  GateWindowTurboSource::PrepareNextRun();

  auto &l = GetThreadLocalData();
  fVoxelPositionGenerator.Get()->fGlobalRotation = l.fGlobalRotation;
  fVoxelPositionGenerator.Get()->fGlobalTranslation = l.fGlobalTranslation;
}

void GateVoxelWTSource::InitializePosition(py::dict) {
  auto &ll = GetThreadLocalDataGenericSource();
  ll.fSPS->SetPosGenerator(fVoxelPositionGenerator.Get());
  // we set a fake value (not used)
  fVoxelPositionGenerator.Get()->SetPosDisType("Point");
}
