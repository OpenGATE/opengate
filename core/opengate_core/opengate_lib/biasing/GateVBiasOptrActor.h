/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVBiasOptrActor_h
#define GateVBiasOptrActor_h

#include "../GateVActor.h"
#include "G4VBiasingOperator.hh"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
    This is a base class (Virtual) to various Operator (Optr) Actors for
   biasing. It inherits from GateVActor (this is an actor) and also from
   G4VBiasingOperator.

    The common operation of all actors that inherit this class is for
    AttachAllLogicalDaughtersVolumes that propagate the actors to all
   sub-volumes. (Later: could be an option to not propagate).

 */

class GateVBiasOptrActor : public G4VBiasingOperator, public GateVActor {
public:
  explicit GateVBiasOptrActor(const std::string &name, py::dict &user_info,
                              bool MT_ready = false);

  void Configure() override;
  void ConfigureForWorker() override;
  void PreUserTrackingAction(const G4Track *track) override;
  virtual void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *volume);
};

#endif
