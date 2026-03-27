/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVChemistryActor_h
#define GateVChemistryActor_h

#include "GateVActor.h"

class GateVChemistryActor : public GateVActor {

public:
  explicit GateVChemistryActor(py::dict &user_info, bool MT_ready = false);

  ~GateVChemistryActor() override = default;

  virtual void StartChemistryTracking(G4Track * /*track*/) {}
  virtual void EndChemistryTracking(G4Track * /*track*/) {}
  virtual void StartProcessing() {}
  virtual void UserPreTimeStepAction() {}
  virtual void UserPostTimeStepAction() {}
  virtual void UserReactionAction(const G4Track & /*trackA*/,
                                  const G4Track & /*trackB*/,
                                  const std::vector<G4Track *> *
                                  /*products*/) {}
  virtual void EndProcessing() {}
};

#endif // GateVChemistryActor_h
