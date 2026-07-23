#include "GateWindowTurboSource.h"
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
  GateSPSVoxelsPosDistribution *fVoxelPositionGenerator;
};
