/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateBOptrBremSplittingActor_h
#define GateBOptrBremSplittingActor_h 1

#include "../GateVActor.h"
#include "G4VBiasingOperator.hh"
#include "GateVBiasOptrActor.h"

namespace py = pybind11;

class GateBremsstrahlungSplittingOptn;

class GateBremsstrahlungSplittingOptrActor : public GateVBiasOptrActor {
public:
  explicit GateBremsstrahlungSplittingOptrActor(py::dict &user_info);
  ~GateBremsstrahlungSplittingOptrActor() override = default;

  G4int fSplittingFactor;
  G4bool fBiasPrimaryOnly;
  G4bool fBiasOnlyOnce;
  G4int fNInteractions;

  void StartRun() override;
  void StartTracking(const G4Track *) override;
  void EndTracking() override {}
  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;

protected:
  G4VBiasingOperation *ProposeNonPhysicsBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */) override;

  G4VBiasingOperation *ProposeOccurenceBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */) override;

  G4VBiasingOperation *ProposeFinalStateBiasingOperation(
      const G4Track *track,
      const G4BiasingProcessInterface *callingProcess) override;

  GateBremsstrahlungSplittingOptn *fBremSplittingOperation;

private:
  // -- Avoid compiler complaining about (wrong) method shadowing,
  // -- this is because other virtual method with same name exists.
  using G4VBiasingOperator::OperationApplied;
};

#endif
