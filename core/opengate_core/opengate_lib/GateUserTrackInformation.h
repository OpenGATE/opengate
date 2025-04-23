/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVActor.h"
#include <G4VUserTrackInformation.hh>

class GateUserTrackInformation : public G4VUserTrackInformation {
public:
  GateUserTrackInformation() = default;
  ~GateUserTrackInformation() override = default;

  void SetGateTrackInformation(GateVActor *myActor, G4bool boolInformation) {
    if (fMapOfTrackInformation.find(myActor) != fMapOfTrackInformation.end())
      fMapOfTrackInformation.erase(myActor);
    fMapOfTrackInformation[myActor] = boolInformation;
  }

  G4bool GetGateTrackInformation(GateVActor *myActor) const {
    return fMapOfTrackInformation.at(myActor);
  }

private:
  std::map<GateVActor *, G4bool> fMapOfTrackInformation;
};
