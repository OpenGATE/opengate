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

  ~GateVBiasOptrActor() override;

  void Configure() override;
  void ConfigureForWorker() override;
  void PreUserTrackingAction(const G4Track *track) override;
  virtual void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *volume);

  /*
   This is a workaround: when running multiple simulations within the same
   process (e.g., using `sim.run(start_new_process=True)`), the
   `GateVBiasOptrActor` instances remain in memory from one run to the next. The
   reason for this behavior is unclear. Checking `fAttachedToVolumeName` acts as
   a "trick" to detect these zombie actors, allowing us to flag them as
   inactive. This flag must be checked in callbacks, as demonstrated in
   `GateGammaFreeFlightOptrActor`.
   */
  bool fIsActive;
};

#endif
