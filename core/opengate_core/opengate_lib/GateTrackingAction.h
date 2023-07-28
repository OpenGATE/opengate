/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTrackingAction_h
#define GateTrackingAction_h

#include "G4Track.hh"
#include "G4UserTrackingAction.hh"
#include "GateVActor.h"

class GateTrackingAction : public G4UserTrackingAction {

public:
  GateTrackingAction();

  virtual ~GateTrackingAction() {}

  void RegisterActor(GateVActor *actor);

  virtual void PreUserTrackingAction(const G4Track *Track);

  virtual void PostUserTrackingAction(const G4Track *Track);

  bool fUserEventInformationFlag;

protected:
  std::vector<GateVActor *> fPreUserTrackingActionActors;
  std::vector<GateVActor *> fPostUserTrackingActionActors;
};

#endif // GateTrackingAction_h
