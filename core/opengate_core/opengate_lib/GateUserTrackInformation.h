/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <G4VUserTrackInformation.hh>
#include "GateVActor.h"

class GateUserTrackInformation : public G4VUserTrackInformation {
public:
  GateUserTrackInformation() = default;
  ~GateUserTrackInformation() override = default;

   void SetGateTrackInformation(GateVActor* myActor,G4bool boolInformation){
    if (fMapOfTrackInformation.find(myActor) != fMapOfTrackInformation.end())
      fMapOfTrackInformation.erase(myActor);
    fMapOfTrackInformation[myActor] = boolInformation;
    }

    G4bool GetGateTrackInformation(GateVActor* myActor){
        return fMapOfTrackInformation[myActor];
    }
int fInfoType;
private :
  std::map<GateVActor*,G4bool> fMapOfTrackInformation;

  
};
