/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTrackingAction_h
#define GateTrackingAction_h

#include "GateVActor.h"
#include "GateVAuxiliaryAttribute.h"
#include <G4Track.hh>
#include <G4UserTrackingAction.hh>
#include <vector>

/*
 * Tracking-action aggregator for both actors and auxiliary attributes.
 *
 * Actors and auxiliary attributes share the same Geant4 tracking hooks but
 * play different roles: actors usually score or write output, while auxiliary
 * attributes expose runtime values and may optionally maintain track state.
 * This class dispatches only the tracking hooks that each registered object
 * explicitly declares.
 */
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
