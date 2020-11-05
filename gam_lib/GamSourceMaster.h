/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSourceMaster_h
#define GamSourceMaster_h

#include "G4VUserPrimaryGeneratorAction.hh"

class GamSourceMaster : public G4VUserPrimaryGeneratorAction {
public:
    void GeneratePrimaries(G4Event *anEvent) override {}
};

#endif // GamSourceMaster_h
