/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDepositedChargeActor_h
#define GateDepositedChargeActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateDepositedChargeActor : public GateVActor {

public:
  explicit GateDepositedChargeActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void StartSimulationAction() override;

  void BeginOfRunAction(const G4Run *run) override;

  void PreUserTrackingAction(const G4Track *track) override;

  void PostUserTrackingAction(const G4Track *track) override;

  void EndOfSimulationWorkerAction(const G4Run *lastRun) override;

  double GetDepositedNominalCharge() const { return fDepositedNominalCharge; }
  double GetDepositedDynamicCharge() const { return fDepositedDynamicCharge; }

protected:
  struct threadLocal_t {
    double fNominalCharge = 0.0; // nominal charge of the particle definition
    double fDynamicCharge = 0.0; // effective charge due to ionisation
  };
  G4Cache<threadLocal_t> threadLocalData;

  // Merged net deposited charge in units of eplus
  double fDepositedNominalCharge;
  double fDepositedDynamicCharge;
};

#endif // GateDepositedChargeActor_h
