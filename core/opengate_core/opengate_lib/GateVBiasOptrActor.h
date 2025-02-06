/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVBiasOptrActor_h
#define GateVBiasOptrActor_h

#include "G4VBiasingOperator.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
    This is a base class (Virtual) to various Operator Actor for biasing.
    It inherits from GateVActor (this is an actor) and also from
   G4VBiasingOperator.
 */

class GateVBiasOptrActor : public G4VBiasingOperator, public GateVActor {
public:
  explicit GateVBiasOptrActor(std::string name, py::dict &user_info,
                              bool MT_ready = false);

  void Configure() override;
  void ConfigureForWorker() override;
  virtual void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *volume);
};

#endif
