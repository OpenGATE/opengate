/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDebugSource_h
#define GateDebugSource_h

#include "GateVSource.h"
#include <G4Polymarker.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateDebugSource : public GateVSource {

public:
  GateDebugSource();
  ~GateDebugSource() override;

  void CleanWorkerThread() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void UpdateActivity(const double time) override;

  double PrepareNextTime(double current_simulation_time,
                         double NumberOfGeneratedEvents) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  double GetDebugValue();

  // thread local structure
  struct threadLocalDebugSource {
    double debug_value = 0.0;
  };
  G4Cache<threadLocalDebugSource> fThreadLocalDataDebugSource;
};

#endif // GateDebugSource_h
