/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTLEUserTrackInformation_h
#define GateTLEUserTrackInformation_h


#include "G4VUserTrackInformation.hh"



class GateTLEUserTrackInformation : public G4VUserTrackInformation {
public:
     GateTLEUserTrackInformation() {};   
     virtual ~GateTLEUserTrackInformation() {};

    void SetTLEDoseBool(G4bool tleInfo){
        fTleInfo = tleInfo;
    }

    G4bool GetTLEDoseBool(){
        return fTleInfo;
    }

private:
G4bool fTleInfo;
};


#endif
