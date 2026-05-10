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
#include "GateVAuxiliaryAttribute.h"
#include "GateVActor.h"
#include <vector>

class GateTrackingAction : public G4UserTrackingAction {

public:
  GateTrackingAction();

  virtual ~GateTrackingAction() {}

  void RegisterActor(GateVActor *actor);

  void RegisterAuxiliaryAttribute(GateVAuxiliaryAttribute *attribute);

  virtual void PreUserTrackingAction(const G4Track *track);

  virtual void PostUserTrackingAction(const G4Track *track);

  bool fUserEventInformationFlag;

protected:
  std::vector<GateVAuxiliaryAttribute *> fPreUserTrackingActionAttributes;
  std::vector<GateVAuxiliaryAttribute *> fPostUserTrackingActionAttributes;
  std::vector<GateVActor *> fPreUserTrackingActionActors;
  std::vector<GateVActor *> fPostUserTrackingActionActors;
};

#endif // GateTrackingAction_h
