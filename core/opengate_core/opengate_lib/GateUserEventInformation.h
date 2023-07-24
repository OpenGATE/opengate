/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateEventUserInfo_h
#define GateEventUserInfo_h

#include "G4VUserEventInformation.hh"
#include "GateVActor.h"
#include <map>

class GateUserEventInformation : public G4VUserEventInformation {

public:
  GateUserEventInformation() = default;

  ~GateUserEventInformation() override = default;

  void Print() const override;

  std::string GetParticleName(G4int track_id);

  void BeginOfEventAction(const G4Event *event);

  void PreUserTrackingAction(const G4Track *track);

protected:
  std::map<G4int, std::string> fMapOfParticleName;
};

#endif // GateEventUserInfo_h
