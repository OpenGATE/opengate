/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateFastY90Source_h
#define GateFastY90Source_h

#include "GateFastY90Kernel.h"
#include "GateVoxelSource.h"

class GateFastY90Source : public GateVoxelSource {
public:
  void InitializeUserInfo(py::dict &user_info) override;
  void PrepareNextRun() override;
  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

protected:
  void InitializePosition(py::dict user_info) override;

private:
  GateFastY90Kernel fKernel;
  G4ParticleDefinition *fPositronDefinition = nullptr;
  bool fUseImage = false;
};

#endif
