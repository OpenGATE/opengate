/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDebugActor_h
#define GateDebugActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateSPRCache.h"
#include "GateVActor.h"
#include "itkImage.h"
#include <memory>

namespace py = pybind11;

class GateDebugActor : public GateVActor {

public:
  explicit GateDebugActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  void BeginOfEventAction(const G4Event *event) override;

  void PreUserTrackingAction(const G4Track *track) override;

  void PostUserTrackingAction(const G4Track *track) override;

  void SteppingAction(G4Step *) override;

  void EndOfEventAction(const G4Event *event) override;

  void EndOfRunAction(const G4Run *run) override;

  int EndOfRunActionMasterThread(int run_id) override;
};

#endif // GateDebugActor_h
