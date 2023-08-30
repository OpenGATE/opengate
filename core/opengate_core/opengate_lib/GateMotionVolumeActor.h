/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMotionVolumeActor_h
#define GateMotionVolumeActor_h

#include "GateVActor.h"
#include "digitizer/GateDigiCollection.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateMotionVolumeActor : public GateVActor {

public:
  explicit GateMotionVolumeActor(py::dict &user_info);

  ~GateMotionVolumeActor() override;

  // Called every time a Run is about to starts in the Master (MT only)
  void MoveGeometry(int run_id);

  // Called every time a Run starts (all threads)
  // void BeginOfRunAction(const G4Run *run) override;

  // Called every time a Run starts (master thread only)
  void BeginOfRunActionMasterThread(int run_id) override;

  void SetTranslations(std::vector<G4ThreeVector> &t);

  void SetRotations(std::vector<G4RotationMatrix> &r);

protected:
  std::vector<G4ThreeVector> fTranslations;
  std::vector<G4RotationMatrix> fRotations;
};

#endif // GateMotionVolumeActor_h
