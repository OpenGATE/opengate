/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateOptrFreeFlightActor_h
#define GateOptrFreeFlightActor_h

#include "G4VBiasingOperator.hh"
#include "GateGammaFreeFlightOptn.h"
#include "GateVBiasOptrActor.h"

namespace py = pybind11;

class GateGammaFreeFlightOptrActor : public GateVBiasOptrActor {

public:
  explicit GateGammaFreeFlightOptrActor(py::dict &user_info);
  ~GateGammaFreeFlightOptrActor() override;

  void InitializeCpp() override;
  void InitializeUserInfo(py::dict &user_info) override;
  void StartTracking(const G4Track *) override;

  void BeginOfEventAction(const G4Event *event) override;
  void SteppingAction(G4Step *step) override;
  void EndOfRunAction(const G4Run *) override;

protected:
  G4VBiasingOperation *
  ProposeNonPhysicsBiasingOperation(const G4Track *,
                                    const G4BiasingProcessInterface *) override;

  G4VBiasingOperation *
  ProposeOccurenceBiasingOperation(const G4Track *,
                                   const G4BiasingProcessInterface *) override;

  G4VBiasingOperation *ProposeFinalStateBiasingOperation(
      const G4Track *track,
      const G4BiasingProcessInterface *callingProcess) override;

  struct threadLocal_t {
    GateGammaFreeFlightOptn *fFreeFlightOperation;
    bool fIsFirstTime;
    bool fIsTrackValidForStep;
  };
  G4Cache<threadLocal_t> threadLocalData;
};

#endif
