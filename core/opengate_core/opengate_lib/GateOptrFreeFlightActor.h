/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateOptrFreeFlightActor_h
#define GateOptrFreeFlightActor_h

#include "G4BOptnForceFreeFlight.hh"
#include "G4EmCalculator.hh"
#include "G4VBiasingOperator.hh"
#include "GateVActor.h"
#include <iostream>
#include <pybind11/stl.h>
namespace py = pybind11;

class GateOptrFreeFlightActor : public G4VBiasingOperator, public GateVActor {

public:
  explicit GateOptrFreeFlightActor(py::dict &user_info);
  ~GateOptrFreeFlightActor() override;

  void InitializeCpp() override;
  void InitializeUserInfo(py::dict &user_info) override;
  void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *volume);

  void Configure() override;
  void ConfigureForWorker() override;
  void StartTracking(const G4Track *) override;

  void PreUserTrackingAction(const G4Track *track) override;
  void PostUserTrackingAction(const G4Track *track) override;

protected:
  G4VBiasingOperation *
  ProposeNonPhysicsBiasingOperation(const G4Track *,
                                    const G4BiasingProcessInterface *) override;

  // -- Used:
  G4VBiasingOperation *
  ProposeOccurenceBiasingOperation(const G4Track *,
                                   const G4BiasingProcessInterface *) override;

  G4VBiasingOperation *ProposeFinalStateBiasingOperation(
      const G4Track *track,
      const G4BiasingProcessInterface *callingProcess) override;

  struct threadLocal_t {
    G4BOptnForceFreeFlight *fFreeFlightOperation;
  };
  G4Cache<threadLocal_t> threadLocalData;
};

#endif
