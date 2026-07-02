/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDepositedChargeActor_h
#define GateDepositedChargeActor_h

#include "GateVActor.h"
#include <G4Cache.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateDepositedChargeActor : public GateVActor {

public:
  explicit GateDepositedChargeActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void StartSimulationAction() override;

  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfEventAction(const G4Event *event) override;

  void PreUserTrackingAction(const G4Track *track) override;

  void PostUserTrackingAction(const G4Track *track) override;

  void EndOfEventAction(const G4Event *event) override;

  void EndOfSimulationWorkerAction(const G4Run *lastRun) override;

  // Net deposited charge, summed over all events
  double GetDepositedNominalCharge() const { return fDepositedNominalCharge; }
  double GetDepositedDynamicCharge() const { return fDepositedDynamicCharge; }

  // Sum of the squared per-event net charge
  double GetDepositedNominalChargeSquared() const {
    return fDepositedNominalChargeSquared;
  }
  double GetDepositedDynamicChargeSquared() const {
    return fDepositedDynamicChargeSquared;
  }

  // Number of primary events (histories) scored
  long long GetNumberOfEvents() const { return fNumberOfEvents; }

protected:
  struct threadLocal_t {
    // Net charge accumulated during the current event only
    double fEventNominalCharge = 0.0;
    double fEventDynamicCharge = 0.0;

    // Running first and second moments over the events scored by this worker.
    double fSumNominalCharge = 0.0;
    double fSumNominalChargeSquared = 0.0;
    double fSumDynamicCharge = 0.0;
    double fSumDynamicChargeSquared = 0.0;

    // Number of events (histories) scored by this worker.
    long long fNumberOfEvents = 0;
  };
  G4Cache<threadLocal_t> threadLocalData;

  // Merged over all workers.
  double fDepositedNominalCharge;        // Sum x
  double fDepositedDynamicCharge;        // Sum x
  double fDepositedNominalChargeSquared; // Sum x^2
  double fDepositedDynamicChargeSquared; // Sum x^2
  long long fNumberOfEvents;             // N
};

#endif // GateDepositedChargeActor_h
