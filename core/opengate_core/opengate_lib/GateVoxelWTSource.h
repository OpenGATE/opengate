#include "GateWindowTurboSource.h"
#include <memory>
class GateSPSVoxelsPosDistribution;

class GateVoxelWTSource : public GateWindowTurboSource {
public:
  GateVoxelWTSource();
  ~GateVoxelWTSource() = default;
  void PrepareNextRun() override;
  GateSPSVoxelsPosDistribution *GetSPSVoxelPosDistribution() {
    return fVoxelPositionGenerator;
  }

protected:
  void InitializePosition(py::dict user_info) override;
  // FIXME: use G4Cache to contains fVoxelPositionGenerator
  GateSPSVoxelsPosDistribution *fVoxelPositionGenerator;
};
