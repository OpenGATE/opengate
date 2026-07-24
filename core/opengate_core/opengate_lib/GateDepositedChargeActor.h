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

  void BeginOfRunActionMasterThread(int run_id) override;

  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfEventAction(const G4Event *event) override;

  void PreUserTrackingAction(const G4Track *track) override;

  void PostUserTrackingAction(const G4Track *track) override;

  void EndOfEventAction(const G4Event *event) override;

  void EndOfRunAction(const G4Run *run) override;

  // Net deposited charge, summed over the events of the current run
  double GetDepositedNominalCharge() const { return fRunNominalCharge; }
  double GetDepositedDynamicCharge() const { return fRunDynamicCharge; }

  // Sum of the squared per-event net charge over the current run
  double GetDepositedNominalChargeSquared() const {
    return fRunNominalChargeSquared;
  }
  double GetDepositedDynamicChargeSquared() const {
    return fRunDynamicChargeSquared;
  }

  // Number of primary events (histories) scored in the current run
  long long GetNumberOfEvents() const { return fRunNumberOfEvents; }

protected:
  // Zero the per-run accumulators (called at construction and before each run).
  void ResetRunAccumulators();

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

  // Accumulators for the current run
  double fRunNominalCharge;
  double fRunDynamicCharge;
  double fRunNominalChargeSquared;
  double fRunDynamicChargeSquared;
  long long fRunNumberOfEvents;
};

#endif // GateDepositedChargeActor_h
