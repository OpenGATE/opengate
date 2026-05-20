#include "GateWindowTurboSource.h"
#include <memory>
class GateSPSVoxelsPosDistribution;

class GateVoxelWTSource : public GateWindowTurboSource {
public:
  GateVoxelWTSource();
  ~GateVoxelWTSource() = default;
  void PrepareNextRun() override;
  GateSPSVoxelsPosDistribution *GetSPSVoxelPosDistribution() {
    return fVoxelPositionGenerator.Get();
  }

protected:
  void InitializePosition(py::dict user_info) override;

  G4Cache<GateSPSVoxelsPosDistribution *> fVoxelPositionGenerator;
};
