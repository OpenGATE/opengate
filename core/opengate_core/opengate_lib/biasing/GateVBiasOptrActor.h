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

   WARNING.
   There is a global static variable in G4VBiasingOperator that
   contains a vector of operators. This variable must be cleared
   once the simulation is done to allow another simulation to be run.
   This cannot be properly done via Geant4 interface (or at least I don't know
   how to do), but we proudly provide an awful trick to do the job, via
   the ClearOperators and GetNonConstBiasingOperators functions

   - GetNonConstBiasingOperators get non const access to the cached static var
   - ClearOperators clear the vector, should be called once everything is done.

 */

class GateVBiasOptrActor : public G4VBiasingOperator, public GateVActor {
public:
  explicit GateVBiasOptrActor(const std::string &name, py::dict &user_info,
                              bool MT_ready = false);

  ~GateVBiasOptrActor() override;

  void InitializeUserInfo(py::dict &user_info) override;
  void Configure() override;
  void ConfigureForWorker() override;
  void PreUserTrackingAction(const G4Track *track) override;
  void SteppingAction(G4Step *step) override;
  virtual void AttachAllLogicalDaughtersVolumes(G4LogicalVolume *volume);

  static void ClearOperators();
  static std::vector<G4VBiasingOperator *> &GetNonConstBiasingOperators();

  bool IsTrackValid(const G4Track *track) const;

  std::vector<std::string> fExcludeVolumes;
  std::vector<const G4LogicalVolume *> fUnbiasedLogicalVolumes;
  double fWeightCutoff;
  double fEnergyCutoff;
};

#endif
